using System;
using System.Collections.Generic;
using System.Net.Sockets;
using System.Net;
using System.Threading;
using Newtonsoft.Json;
using System.Reflection;
using Modding;
using UnityEngine;
using UObject = UnityEngine.Object;
using GlobalEnums;
using System.Collections;

namespace SuperFancyInteropMod
{
    internal class Bridge
    {
        private readonly string host;
        private readonly int port;
        private readonly UdpClient udpClient;
        private readonly IPEndPoint clientEndPoint;
    private Thread updateThread;
        private bool isRunning = true;
        private const int UPDATE_RATE_MS = 33; // ~30 FPS
    public static readonly float UPDATE_RATE_S = UPDATE_RATE_MS / 1000f;
    // Queue for messages created on main thread and sent on sender thread
    private readonly Queue<byte[]> sendQueue = new Queue<byte[]>();
    private readonly object queueLock = new object();

        public Bridge(string host, int port)
        {
            this.host = host;
            this.port = port;
            // Always use IPv4
            this.udpClient = new UdpClient(AddressFamily.InterNetwork);
            var addresses = Dns.GetHostAddresses(host);
            IPAddress ipv4 = null;
            foreach (var addr in addresses)
            {
                if (addr.AddressFamily == AddressFamily.InterNetwork)
                {
                    ipv4 = addr;
                    break;
                }
            }
            if (ipv4 == null)
                throw new ArgumentException($"Could not resolve an IPv4 address for host: {host}");
            this.clientEndPoint = new IPEndPoint(ipv4, port);
        }

        public void StartSending()
        {
            updateThread = new Thread(() => {
                // Active ping/pong handshake: send ping to Python and wait for a JSON pong reply
                Modding.Logger.Log("Pinging Python bridge to check readiness...");
                udpClient.Client.ReceiveTimeout = 1000; // 1 second timeout for receive
                bool pythonReady = false;
                var pingMessage = new Dictionary<string, object> { { "type", "ping" } };
                var pingJson = JsonConvert.SerializeObject(pingMessage);
                var pingBytes = System.Text.Encoding.UTF8.GetBytes(pingJson);

                while (!pythonReady && isRunning)
                {
                    try
                    {
                        // send ping
                        udpClient.Send(pingBytes, pingBytes.Length, clientEndPoint);

                        // try to receive a reply
                        IPEndPoint tempEndPoint = new IPEndPoint(IPAddress.Any, 0);
                        var received = udpClient.Receive(ref tempEndPoint);
                        if (received != null && received.Length > 0)
                        {
                            var msg = System.Text.Encoding.UTF8.GetString(received);
                            try
                            {
                                var parsed = JsonConvert.DeserializeObject<Dictionary<string, object>>(msg);
                                if (parsed != null && parsed.TryGetValue("type", out var t) && (t.ToString().ToLower() == "pong" || t.ToString().ToLower() == "ready"))
                                {
                                    pythonReady = true;
                                    Modding.Logger.Log("Received pong from Python program. Starting state updates.");
                                    break;
                                }
                            }
                            catch (Exception)
                            {
                                // ignore non-json replies
                            }
                        }
                    }
                    catch (SocketException) { /* timeout or no data, keep waiting */ }
                    catch (Exception ex)
                    {
                        Modding.Logger.Log("Error during handshake ping: " + ex.Message);
                    }

                    Thread.Sleep(500);
                }

                if (pythonReady)
                {
                    // Enter sender loop: only read from sendQueue and transmit
                    Modding.Logger.Log("Entering UDP sender loop");
                    while (isRunning)
                    {
                        try
                        {
                            byte[] toSend = null;
                            lock (queueLock)
                            {
                                if (sendQueue.Count > 0)
                                    toSend = sendQueue.Dequeue();
                            }
                            if (toSend != null)
                            {
                                udpClient.Send(toSend, toSend.Length, clientEndPoint);
                            }
                            else
                            {
                                Thread.Sleep(UPDATE_RATE_MS);
                            }
                        }
                        catch (Exception ex)
                        {
                            Modding.Logger.Log("Error in UDP sender loop: " + ex.Message);
                            Thread.Sleep(1000);
                        }
                    }
                }
                else
                {
                    Modding.Logger.Log("Stopped waiting for Python program (isRunning = false)");
                }
            });
            updateThread.IsBackground = true;
            updateThread.Start();
            Modding.Logger.Log($"Started sending state updates to {host}:{port} at {1000.0/UPDATE_RATE_MS:F1} FPS");
        }

        private void SendStateUpdates()
        {
            Modding.Logger.Log("Starting state update loop");
            while (isRunning)
            {
                try
                {
                    // Only send updates if player is in a gameplay scene
                    if (GameManager.instance != null && GameManager.instance.IsGameplayScene())
                    {
                        var gameState = GetCurrentState();
                        var message = new Dictionary<string, object>
                        {
                            { "type", "full_update" },
                            { "state", gameState }
                        };
                        SendMessage(message);
                    }
                    Thread.Sleep(UPDATE_RATE_MS);
                }
                catch (Exception ex)
                {
                    if (isRunning) // Only log if we're still supposed to be running
                    {
                        Modding.Logger.Log("Error in SendStateUpdates: " + ex.Message);
                        Thread.Sleep(1000); // Wait longer on error
                    }
                }
            }
        }

        private void SendMessage(Dictionary<string, object> message)
        {
            try
            {
                var messageJson = JsonConvert.SerializeObject(message);
                var messageBytes = System.Text.Encoding.UTF8.GetBytes(messageJson);
                
                // Check if message is too large for UDP (typical limit is around 64KB)
                const int maxUdpSize = 32768; // 32KB to be safe
                if (messageBytes.Length > maxUdpSize)
                {
                    Modding.Logger.Log($"Message too large ({messageBytes.Length} bytes), skipping");
                    return;
                }
                
                udpClient.Send(messageBytes, messageBytes.Length, clientEndPoint);
            }
            catch (Exception ex)
            {
                Modding.Logger.Log("Error sending message: " + ex.Message);
            }
        }

    public Dictionary<string, object> GetCurrentState()
        {
            try
            {
                var state = new Dictionary<string, object>();

                // Get player health
                var playerHealth = GetPlayerHealth();
                state["player_health"] = playerHealth;

                // Get player position
                var playerPosition = GetPlayerPosition();
                state["player_position"] = playerPosition;

                // Get hitboxes from current scene
                var hitboxes = GetSceneHitboxes();
                state["hitboxes"] = hitboxes;

                // Get all enemies on screen with their health
                var enemies = GetEnemiesOnScreen();
                state["enemies"] = enemies;

                return state;
            }
            catch (Exception ex)
            {
                Modding.Logger.Log("Error getting current state: " + ex.Message);
                return new Dictionary<string, object>
                {
                    { "error", ex.Message }
                };
            }
        }

        private Dictionary<string, object> GetPlayerHealth()
        {
            try
            {
                var health = new Dictionary<string, object>();
                
                // Get PlayerData instance for health information
                var playerData = PlayerData.instance;
                if (playerData != null)
                {
                    health["current"] = playerData.health;
                    health["max"] = playerData.maxHealth;
                    health["blue"] = playerData.healthBlue;
                }
                else
                {
                    health["current"] = 0;
                    health["max"] = 0;
                    health["blue"] = 0;
                }

                return health;
            }
            catch (Exception ex)
            {
                Modding.Logger.Log("Error getting player health: " + ex.Message);
                return new Dictionary<string, object>
                {
                    { "current", 0 },
                    { "max", 0 },
                    { "blue", 0 }
                };
            }
        }

        private Dictionary<string, object> GetPlayerPosition()
        {
            try
            {
                var position = new Dictionary<string, object>();
                
                var heroController = HeroController.instance;
                if (heroController != null)
                {
                    var pos = heroController.transform.position;
                    position["x"] = Math.Round(pos.x, 2);
                    position["y"] = Math.Round(pos.y, 2);
                }
                else
                {
                    position["x"] = 0.0;
                    position["y"] = 0.0;
                }

                return position;
            }
            catch (Exception ex)
            {
                Modding.Logger.Log("Error getting player position: " + ex.Message);
                return new Dictionary<string, object>
                {
                    { "x", 0.0 },
                    { "y", 0.0 }
                };
            }
        }

        // ReSharper disable once StructCanBeMadeReadOnly
        public struct HitboxType
        {
            public static readonly HitboxType Knight = new("Knight", 0);                     // yellow
            public static readonly HitboxType Enemy = new("Enemy", 1);       // red      
            public static readonly HitboxType Attack = new("Attack", 2);                       // cyan
            public static readonly HitboxType Terrain = new("Terrain", 3);     // green
            public static readonly HitboxType Trigger = new("Trigger", 4); // blue
            public static readonly HitboxType Breakable = new("Breakable", 5); // pink
            public static readonly HitboxType Gate = new("Gate", 6); // dark blue
            public static readonly HitboxType HazardRespawn = new("HazardRespawn", 7); // purple 
            public static readonly HitboxType Other = new("Other", 8); // orange
            public static readonly HitboxType None = new("None", 9); // orange

            public readonly string Name;
            public readonly int Depth;

            public HitboxType(string name, int depth)
            {
                Name = name;
                Depth = depth;
            }
        }
        
        public static HitboxType TryAddHitboxes(Collider2D collider2D)
        {
            if (collider2D == null)
                return HitboxType.None;

            // Only process supported collider types
            if (!(collider2D is BoxCollider2D || collider2D is PolygonCollider2D || collider2D is EdgeCollider2D || collider2D is CircleCollider2D))
                return HitboxType.None;

            var go = collider2D.gameObject;
            if (go == null)
                return HitboxType.None;

            // Enemy hitbox
            if (collider2D.GetComponent<DamageHero>() != null || go.LocateMyFSM("damages_hero") != null)
                return HitboxType.Enemy;

            // Other (enemy health manager)
            if (go.GetComponent<HealthManager>() != null || go.LocateMyFSM("health_manager_enemy") != null || go.LocateMyFSM("health_manager") != null)
                return HitboxType.Other;

            // Terrain and breakable
            if (go.layer == (int)PhysLayers.TERRAIN)
            {
                if (go.name.Contains("Breakable") || go.name.Contains("Collapse") || go.GetComponent<Breakable>() != null)
                    return HitboxType.Breakable;
                else
                    return HitboxType.Terrain;
            }

            // Player
            if (HeroController.instance != null && go == HeroController.instance.gameObject && !collider2D.isTrigger)
                return HitboxType.Knight;

            // Attack
            if (go.GetComponent<DamageEnemies>() != null || go.LocateMyFSM("damages_enemy") != null || (go.name == "Damager" && go.LocateMyFSM("Damage") != null))
                return HitboxType.Attack;

            // Hazard respawn
            if (collider2D.isTrigger && collider2D.GetComponent<HazardRespawnTrigger>() != null)
                return HitboxType.HazardRespawn;

            // Gate
            if (collider2D.isTrigger && collider2D.GetComponent<TransitionPoint>() != null)
                return HitboxType.Gate;

            // Trigger (breakable, not a bouncer)
            if (collider2D.GetComponent<Breakable>() != null)
            {
                var bounce = collider2D.GetComponent<NonBouncer>();
                if (bounce == null || !bounce.active)
                    return HitboxType.Trigger;
                return HitboxType.None;
            }

            // Fallback
            return HitboxType.Other;
        }

        private List<Dictionary<string, object>> GetSceneHitboxes()
        {
            var hitboxes = new List<Dictionary<string, object>>();
            try
            {
                var colliders = UObject.FindObjectsOfType<Collider2D>();
                int count = 0;
                const int maxHitboxes = 80;
                foreach (var collider in colliders)
                {
                    if (count >= maxHitboxes) break;
                    if (collider == null) continue;
                    var go = collider.gameObject;
                    if (go == null || !go.activeInHierarchy) continue;
                    var hitboxType = TryAddHitboxes(collider);
                    // Only include hitboxes with Depth < 8 (like Abstraction)
                    if (hitboxType.Depth < 8)
                    {
                        var bounds = collider.bounds;
                        var hitboxData = new Dictionary<string, object>
                        {
                            { "name", go.name },
                            { "type", hitboxType.Name },
                            { "bounds", new Dictionary<string, object>
                                {
                                    { "x", Math.Round(bounds.center.x, 2) },
                                    { "y", Math.Round(bounds.center.y, 2) },
                                    { "w", Math.Round(bounds.size.x, 2) },
                                    { "h", Math.Round(bounds.size.y, 2) }
                                }
                            }
                        };
                        hitboxes.Add(hitboxData);
                        count++;
                    }
                }
            }
            catch (Exception ex)
            {
                Modding.Logger.Log("Error getting hitboxes: " + ex.Message);
            }
            return hitboxes;
        }

        private List<Dictionary<string, object>> GetEnemiesOnScreen()
        {
            var enemies = new List<Dictionary<string, object>>();
            
            try
            {
                // Find all HealthManager components (enemies typically have these)
                var healthManagers = UObject.FindObjectsOfType<HealthManager>();
                var count = 0;
                const int maxEnemies = 20; // Limit number of enemies
                
                foreach (var healthManager in healthManagers)
                {
                    if (count >= maxEnemies) break;
                    
                    if (healthManager != null && 
                        healthManager.gameObject.activeInHierarchy && 
                        healthManager.gameObject != HeroController.instance?.gameObject) // Exclude player
                    {
                        var enemyData = new Dictionary<string, object>
                        {
                            { "name", healthManager.gameObject.name },
                            { "x", Math.Round(healthManager.transform.position.x, 2) },
                            { "y", Math.Round(healthManager.transform.position.y, 2) },
                            { "hp", healthManager.hp }
                        };

                        // Try to get collider bounds if available (simplified)
                        var collider = healthManager.GetComponent<Collider2D>();
                        if (collider != null)
                        {
                            enemyData["w"] = Math.Round(collider.bounds.size.x, 2);
                            enemyData["h"] = Math.Round(collider.bounds.size.y, 2);
                        }
                        
                        enemies.Add(enemyData);
                        count++;
                    }
                }
            }
            catch (Exception ex)
            {
                Modding.Logger.Log("Error getting enemies: " + ex.Message);
            }
            
            return enemies;
        }

        public void Stop()
        {
            isRunning = false;
            udpClient?.Close();
            updateThread?.Join(1000); // Wait up to 1 second for thread to finish
            Modding.Logger.Log("Bridge stopped");
        }

        // Called from Unity main thread behaviour to enqueue serialized messages
        public void EnqueueMessage(byte[] message)
        {
            lock (queueLock)
            {
                sendQueue.Enqueue(message);
            }
        }

        public bool IsRunning => isRunning;
    }
}

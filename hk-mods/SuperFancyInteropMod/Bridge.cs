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

        public Bridge(string host, int port)
        {
            this.host = host;
            this.port = port;
            this.udpClient = new UdpClient();
            // Use Dns.GetHostAddresses to resolve hostnames like 'localhost'
            var addresses = Dns.GetHostAddresses(host);
            if (addresses == null || addresses.Length == 0)
                throw new ArgumentException($"Could not resolve host: {host}");
            this.clientEndPoint = new IPEndPoint(addresses[0], port);
        }

        public void StartSending()
        {
            updateThread = new Thread(SendStateUpdates);
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
                    var gameState = GetCurrentState();
                    var message = new Dictionary<string, object>
                    {
                        { "type", "full_update" },
                        { "state", gameState }
                    };
                    
                    SendMessage(message);
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

        private Dictionary<string, object> GetCurrentState()
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

            private HitboxType(string name, int depth)
            {
                Name = name;
                Depth = depth;
            }
        }
        
        public static HitboxType TryAddHitboxes(Collider2D collider2D)
        {
             if (collider2D == null)   {  
                return HitboxType.None;
            }

            if (collider2D is BoxCollider2D or PolygonCollider2D or EdgeCollider2D or CircleCollider2D)
            {
                GameObject go = collider2D.gameObject;
                if (collider2D.GetComponent<DamageHero>() || collider2D.gameObject.LocateMyFSM("damages_hero"))
                {
                    return HitboxType.Enemy;
                }
                else if (go.GetComponent<HealthManager>() || go.LocateMyFSM("health_manager_enemy") || go.LocateMyFSM("health_manager"))
                {
                    return HitboxType.Other;
                }
                else if (go.layer == (int)PhysLayers.TERRAIN)
                {
                    if (go.name.Contains("Breakable") || go.name.Contains("Collapse") || go.GetComponent<Breakable>() != null) return HitboxType.Breakable;
                    else return HitboxType.Terrain;
                }
                else if (go == HeroController.instance?.gameObject && !collider2D.isTrigger)
                {
                    return HitboxType.Knight;
                }
                else if (go.GetComponent<DamageEnemies>() || go.LocateMyFSM("damages_enemy") || go.name == "Damager" && go.LocateMyFSM("Damage"))
                {
                    return HitboxType.Attack;
                }
                else if (collider2D.isTrigger && collider2D.GetComponent<HazardRespawnTrigger>())
                {
                    return HitboxType.HazardRespawn;
                }
                else if (collider2D.isTrigger && collider2D.GetComponent<TransitionPoint>())
                {
                    return HitboxType.Gate;
                }
                else if (collider2D.GetComponent<Breakable>())
                {
                    NonBouncer bounce = collider2D.GetComponent<NonBouncer>();
                    if (bounce == null || !bounce.active)
                    {
                        return HitboxType.Trigger;
                    }
                    return HitboxType.None;
                }
                else
                {
                    return HitboxType.Other;
                }
            }
            return HitboxType.None;
        }

        private List<Dictionary<string, object>> GetSceneHitboxes()
        {
            var hitboxes = new List<Dictionary<string, object>>();
            
            try
            {
                var colliders = UObject.FindObjectsOfType<Collider2D>();
                var count = 0;
                const int maxHitboxes = 80; 
                
                foreach (var collider in colliders)
                {
                    if (count >= maxHitboxes) break;
                    
                    if (collider != null && collider.gameObject.activeInHierarchy)
                    {
                        var hitboxType = TryAddHitboxes(collider);
                        if (hitboxType.Name != "None")
                        {
                            var hitboxData = new Dictionary<string, object>
                            {
                                { "name", collider.gameObject.name },
                                { "type", hitboxType.Name },
                                { "bounds", new Dictionary<string, object>
                                    {
                                        { "x", Math.Round(collider.bounds.center.x, 2) },
                                        { "y", Math.Round(collider.bounds.center.y, 2) },
                                        { "w", Math.Round(collider.bounds.size.x, 2) },
                                        { "h", Math.Round(collider.bounds.size.y, 2) }
                                    }
                                }
                            };
                            
                            hitboxes.Add(hitboxData);
                            count++;
                        }
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
    }
}

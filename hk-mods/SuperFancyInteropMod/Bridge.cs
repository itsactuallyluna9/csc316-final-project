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
        private Thread listeningThread;
        private bool isListening = true;
        private IPEndPoint clientEndPoint;

        public Bridge(string host, int port)
        {
            this.host = host;
            this.port = port;
            this.udpClient = new UdpClient(port);
        }

        public void StartListening()
        {
            listeningThread = new Thread(Listen);
            listeningThread.IsBackground = true;
            listeningThread.Start();
            Modding.Logger.Log("Started listening thread on port " + port);
        }

        private void Listen()
        {
            Modding.Logger.Log("UDP Server listening on port " + port);
            
            while (isListening)
            {
                try
                {
                    IPEndPoint remoteEndPoint = new IPEndPoint(IPAddress.Any, 0);
                    byte[] receivedBytes = udpClient.Receive(ref remoteEndPoint);
                    
                    // Store the client endpoint for sending responses
                    clientEndPoint = remoteEndPoint;
                    
                    var message = System.Text.Encoding.UTF8.GetString(receivedBytes);
                    var data = JsonConvert.DeserializeObject<Dictionary<string, object>>(message);
                    Modding.Logger.Log("Got a message: " + message);
                    HandleMessage(data);
                }
                catch (SocketException ex)
                {
                    if (isListening) // Only log if we're still supposed to be listening
                    {
                        Modding.Logger.Log("Socket error: " + ex.Message);
                    }
                }
                catch (Exception ex)
                {
                    Modding.Logger.Log("Error in Listen: " + ex.Message);
                }
            }
        }

        private void HandleMessage(Dictionary<string, object> message)
        {
            try
            {
                if (message.ContainsKey("type"))
                {
                    switch (message["type"].ToString())
                    {
                        case "reset":
                            // Handle reset
                            Modding.Logger.Log("Handling reset request");
                            // TODO: Implement actual reset logic here
                            
                            var response = new Dictionary<string, object>
                            {
                                { "type", "reset_done" }
                            };
                            SendResponse(response);
                            break;
                            
                        case "get_state":
                            // Handle get state request
                            Modding.Logger.Log("Handling get_state request");
                            var stateResponse = GetCurrentState();
                            SendResponse(stateResponse);
                            break;
                            
                        default:
                            Modding.Logger.Log("Unknown message type: " + message["type"]);
                            break;
                    }
                }
                else
                {
                    // This is an input message (no "type" field means it's input data)
                    HandleInput(message);
                }
            }
            catch (Exception ex)
            {
                Modding.Logger.Log("Error handling message: " + ex.Message);
            }
        }

        private void HandleInput(Dictionary<string, object> message)
        {
            try
            {
                Modding.Logger.Log("Handling input");
                
                // Get the HeroController - you might need to adjust this based on your game's structure
                HeroController heroController = HeroController.instance;
                if (heroController == null)
                {
                    Modding.Logger.Log("HeroController not found!");
                    return;
                }

                // Parse input values safely
                bool left = message.ContainsKey("left") && Convert.ToBoolean(message["left"]);
                bool right = message.ContainsKey("right") && Convert.ToBoolean(message["right"]);
                bool jump = message.ContainsKey("jump") && Convert.ToBoolean(message["jump"]);
                bool attack = message.ContainsKey("attack") && Convert.ToBoolean(message["attack"]);

                // Apply movement input
                if (left && !right)
                {
                    heroController.move_input = -127f; // Left is typically negative
                }
                else if (right && !left)
                {
                    heroController.move_input = 127f; // Right is typically positive
                }
                else
                {
                    heroController.move_input = 0f; // No movement or both pressed
                }

                // Apply jump input
                if (jump)
                {
                    heroController.vertical_input = 127f;
                }
                else
                {
                    heroController.vertical_input = 0f;
                }

                // Apply attack input
                if (attack)
                {
                    // You might need to adjust this based on how attacks work in your game
                    if (heroController.cState != null)
                    {
                        heroController.cState.attacking = true;
                    }
                }

                Modding.Logger.Log($"Input processed - Left: {left}, Right: {right}, Jump: {jump}, Attack: {attack}");
            }
            catch (Exception ex)
            {
                Modding.Logger.Log("Error handling input: " + ex.Message);
            }
        }

        private void SendResponse(Dictionary<string, object> response)
        {
            try
            {
                if (clientEndPoint != null)
                {
                    var responseMessage = JsonConvert.SerializeObject(response);
                    var responseBytes = System.Text.Encoding.UTF8.GetBytes(responseMessage);
                    
                    // Check if message is too large for UDP (typical limit is around 64KB, but let's be safe)
                    const int maxUdpSize = 32768; // 32KB
                    if (responseBytes.Length > maxUdpSize)
                    {
                        Modding.Logger.Log($"Message too long ({responseBytes.Length} bytes), sending error response");
                        var errorResponse = new Dictionary<string, object>
                        {
                            { "type", "error" },
                            { "message", "Response too large for UDP transmission" },
                            { "size", responseBytes.Length }
                        };
                        var errorMessage = JsonConvert.SerializeObject(errorResponse);
                        var errorBytes = System.Text.Encoding.UTF8.GetBytes(errorMessage);
                        udpClient.Send(errorBytes, errorBytes.Length, clientEndPoint);
                        return;
                    }
                    
                    udpClient.Send(responseBytes, responseBytes.Length, clientEndPoint);
                    Modding.Logger.Log($"Sent response ({responseBytes.Length} bytes)");
                }
            }
            catch (Exception ex)
            {
                Modding.Logger.Log("Error sending response: " + ex.Message);
            }
        }

        private Dictionary<string, object> GetCurrentState()
        {
            try
            {
                var state = new Dictionary<string, object>
                {
                    { "type", "state" }
                };

                // Get player health
                var playerHealth = GetPlayerHealth();
                state["player_health"] = playerHealth;

                // Get hitboxes from current scene
                var hitboxes = GetSceneHitboxes();
                state["hitboxes"] = hitboxes;

                // Get all enemies on screen with their health
                var enemies = GetEnemiesOnScreen();
                state["enemies"] = enemies;

                Modding.Logger.Log($"State collected - Player Health: {playerHealth}, Hitboxes: {hitboxes.Count}, Enemies: {enemies.Count}");

                return state;
            }
            catch (Exception ex)
            {
                Modding.Logger.Log("Error getting current state: " + ex.Message);
                return new Dictionary<string, object>
                {
                    { "type", "state" },
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
            isListening = false;
            udpClient?.Close();
            listeningThread?.Join(1000); // Wait up to 1 second for thread to finish
            Modding.Logger.Log("Bridge stopped");
        }
    }
}

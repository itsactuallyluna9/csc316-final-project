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
using System.Collections;
using Microsoft.Extensions.Logging;

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
                    udpClient.Send(responseBytes, responseBytes.Length, clientEndPoint);
                    Modding.Logger.Log("Sent response: " + responseMessage);
                }
            }
            catch (Exception ex)
            {
                Modding.Logger.Log("Error sending response: " + ex.Message);
            }
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

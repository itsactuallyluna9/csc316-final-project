using System;
using System.Collections.Generic;
using System.Net.Sockets;
using System.Threading;
using Newtonsoft.Json;

namespace SuperFancyInteropMod
{
    internal class Bridge
    {

        private readonly string host;
        private readonly int port;
        private readonly Socket sock;
        private Thread listeningThread;
        
        public Bridge(string host, int port)
        {
            this.host = host;
            this.port = port;
            this.sock = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
        }

        public void StartListening()
        {
            listeningThread = new Thread(Listen);
            listeningThread.Start();
        }

        private void Listen()
        {
            var endPoint = new System.Net.IPEndPoint(System.Net.IPAddress.Any, 0);
            while (true)
            {
                var buffer = new byte[4096];
                int received = sock.ReceiveFrom(buffer, ref endPoint);
                var message = System.Text.Encoding.UTF8.GetString(buffer, 0, received);
                var data = JsonConvert.DeserializeObject<Dictionary<string, object>>(message);
                HandleMessage(data);
            }
        }

        private void HandleMessage(Dictionary<string, object> message)
        {
            switch (message["type"].ToString())
            {
                case "reset":
                    // Handle reset
                    break;
                case "input":
                // Handle input
                default:
                    Console.WriteLine("Unknown message type: " + message["type"]);
                    break;
            }
            // Handle incoming messages here
            Console.WriteLine("Received message: " + JsonConvert.SerializeObject(message));
        }
    }
}

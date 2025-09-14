using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using Modding;
using UnityEngine;
using UObject = UnityEngine.Object;

namespace SuperFancyInteropMod
{
    internal class SuperFancyInteropMod : Mod
    {
        internal static SuperFancyInteropMod Instance { get; private set; }

        internal Bridge bridge;

        public SuperFancyInteropMod() : base("Super Fancy Interop Mod") { }

        public override string GetVersion()
        {
            return Assembly.GetExecutingAssembly().GetName().Version.ToString();
        }

        public override void Initialize()
        {
            Log("Initializing");

            Instance = this;

            bridge = new Bridge("localhost", 9999);
            bridge.StartSending();

            // Create a GameObject with BridgeBehaviour to collect state on Unity main thread
            try
            {
                var go = new GameObject("SuperFancyInterop_Bridge");
                UObject.DontDestroyOnLoad(go);
                var behaviour = go.AddComponent<BridgeBehaviour>();
                if (behaviour != null)
                {
                    behaviour.bridge = bridge;
                }
            }
            catch (Exception ex)
            {
                Log("Failed to create BridgeBehaviour: " + ex.Message);
            }

            Log("Initialized");
        }
    }
}

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
            bridge.StartListening();

            Log("Initialized");
        }
    }
}

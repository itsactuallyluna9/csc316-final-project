using System.Collections.Generic;
using UnityEngine;
using Newtonsoft.Json;
using Modding;

namespace SuperFancyInteropMod
{
    public class BridgeBehaviour : MonoBehaviour
    {
    internal Bridge bridge;
        private float accumulator = 0f;

        void Update()
        {
            if (bridge == null || !bridge.IsRunning) return;

            accumulator += Time.deltaTime;
            if (accumulator < Bridge.UPDATE_RATE_S) return;
            accumulator = 0f;

            try
            {
                var state = bridge.GetCurrentState();
                var message = new Dictionary<string, object>
                {
                    { "type", "full_update" },
                    { "state", state }
                };
                var json = JsonConvert.SerializeObject(message);
                var bytes = System.Text.Encoding.UTF8.GetBytes(json);
                bridge.EnqueueMessage(bytes);
            }
            catch (System.Exception ex)
            {
                Modding.Logger.Log("BridgeBehaviour.Update error: " + ex.Message);
            }
        }
    }
}

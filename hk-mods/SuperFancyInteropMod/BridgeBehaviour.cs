using System.Collections.Generic;
using UnityEngine;
using Newtonsoft.Json;
using UnityEngine.Tilemaps;
using Modding;

namespace SuperFancyInteropMod
{
    public class BridgeBehaviour : MonoBehaviour
    {
    internal Bridge bridge;
        private float accumulator = 0f;
        private bool dumpedColliders = false;
        private bool loggedEarlyReturn = false;

        void Awake()
        {
            Modding.Logger.Log("BridgeBehaviour Awake");
        }

        void OnEnable()
        {
            Modding.Logger.Log("BridgeBehaviour OnEnable");
        }

        void Update()
        {
            if (bridge == null || !bridge.IsRunning)
            {
                if (!loggedEarlyReturn)
                {
                    Modding.Logger.Log($"BridgeBehaviour early return: bridge={(bridge==null?"null":"set")}, IsRunning={(bridge==null?"<no-bridge>":bridge.IsRunning.ToString())}");
                    loggedEarlyReturn = true;
                }
                return;
            }

            accumulator += Time.deltaTime;
            if (accumulator < Bridge.UPDATE_RATE_S) return;
            accumulator = 0f;

            try
            {
                if (!dumpedColliders)
                {
                    DumpColliderSample();
                    dumpedColliders = true;
                }
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
        
        private void DumpColliderSample()
        {
            try
            {
                var all = Object.FindObjectsOfType<Collider2D>();
                Modding.Logger.Log($"Collider dump: total={all.Length}");

                var typeCounts = new Dictionary<string, int>();
                var layerCounts = new Dictionary<int, int>();

                for (int i = 0; i < all.Length; i++)
                {
                    var c = all[i];
                    if (c == null) continue;

                    var go = c.gameObject;
                    var name = go != null ? go.name : "<null>";
                    var tag = go != null ? go.tag : "<null>";
                    var layer = go != null ? go.layer : -1;
                    var layerName = go != null ? LayerMask.LayerToName(go.layer) : "<null>";
                    var active = go != null ? go.activeInHierarchy.ToString() : "false";
                    var enabled = c.enabled.ToString();
                    var isTrigger = c.isTrigger.ToString();
                    var type = c.GetType().Name;
                    var size = c.bounds.size;
                    var boundsStr = $"({size.x:F2},{size.y:F2},{size.z:F2})";
                    var tilemap = c.GetComponent<Tilemap>();
                    var hasTilemap = tilemap != null ? "yes" : "no";

                    // Update summaries
                    if (!typeCounts.ContainsKey(type)) typeCounts[type] = 0;
                    typeCounts[type]++;
                    if (!layerCounts.ContainsKey(layer)) layerCounts[layer] = 0;
                    layerCounts[layer]++;

                    Modding.Logger.Log($"Collider[{i}]: name={name}, tag={tag}, layer={layer}({layerName}), active={active}, enabled={enabled}, isTrigger={isTrigger}, type={type}, size={boundsStr}, tilemap={hasTilemap}");
                }

                Modding.Logger.Log("Collider type counts:");
                foreach (var kv in typeCounts)
                {
                    Modding.Logger.Log($"  {kv.Key}: {kv.Value}");
                }

                Modding.Logger.Log("Collider layer counts:");
                foreach (var kv in layerCounts)
                {
                    Modding.Logger.Log($"  {kv.Key}: {kv.Value}");
                }
            }
            catch (System.Exception ex)
            {
                Modding.Logger.Log("Error dumping colliders: " + ex.Message);
            }
        }
    }
}

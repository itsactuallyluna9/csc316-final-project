using Modding;
using System.Collections.Generic;
using UnityEngine;


namespace Abstraction
{
    public class Abstraction : Mod
    {
        public Abstraction() : base("HitboxOnly") { }
        public override string GetVersion() => "1.3.0.0";
        public override void Initialize(Dictionary<string, Dictionary<string, GameObject>> preloadedObjects)
        {
            UnityEngine.SceneManagement.SceneManager.sceneLoaded += SceneManager_sceneLoaded;
        }
        private void SceneManager_sceneLoaded(UnityEngine.SceneManagement.Scene arg0, UnityEngine.SceneManagement.LoadSceneMode arg1)
        {
            if (HeroController.SilentInstance != null && Camera.main.GetComponent<WhiteOcclusion>() == null)
            {
                Camera.main.gameObject.AddComponent<WhiteOcclusion>();
            }
            foreach (GameObject gameObject in Resources.FindObjectsOfTypeAll<GameObject>())
            {
                var good = false;
                if (gameObject.GetComponent<HitboxRender>() != null)
                {
                    continue;
                }
                foreach (var c in gameObject.GetComponents<Collider2D>())
                {
                    if (HitboxRender.TryAddHitboxes(c).Depth < 8)
                    {
                        good = true;
                    }
                }
                if (good)
                {
                    gameObject.AddComponent<HitboxRender>();
                }
            }
        }
    }
}

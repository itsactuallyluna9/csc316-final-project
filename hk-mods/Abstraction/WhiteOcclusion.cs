
using Modding;
using System.Collections.Generic;
using UnityEngine;


namespace Abstraction
{
    public class WhiteOcclusion : MonoBehaviour
    {
        private void OnRenderImage(RenderTexture src, RenderTexture dest)
        {
            if(HeroController.SilentInstance == null)
            {
                Graphics.Blit(src, dest);
                Destroy(this);
                return;
            }
            Graphics.Blit(Texture2D.grayTexture, dest);
        }
    }
}

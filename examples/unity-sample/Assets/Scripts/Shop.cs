using UnityEngine;
using UnityEngine.Advertisements;
using UnityEngine.Purchasing;

public class Shop : MonoBehaviour
{
    void Start()
    {
        Advertisement.Initialize("1234567");
        UnityPurchasing.Initialize(this, ConfigurationBuilder.Instance(StandardPurchasingModule.Instance()));
    }

    public void OpenLootBox() { var reward = Random.Range(0, 100); }
}

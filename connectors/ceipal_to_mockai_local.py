import sys, os, json, requests
from collections.abc import Iterable

# === Ensure hrflow-connectors is in Python path ===
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "hrflow-connectors/src")))

from hrflow_connectors.v1.connectors.ceipal.connector import Ceipal
from hrflow_connectors.v1.connectors.hrflow.warehouse import HrFlowProfileWarehouse

_collected_profiles = []

class LocalWriter:
    """Intercepts HrFlow writes and saves data locally instead."""
    def parameters(self, **kwargs):
        return self

    def __call__(self, profiles, *args, **kwargs):
        global _collected_profiles
        print(f"\n LocalWriter.__call__ invoked with {len(profiles) if isinstance(profiles, list) else 1} profiles")

        simplified = []
        for p in profiles if isinstance(profiles, Iterable) else [profiles]:
            if hasattr(p, "to_dict"):
                simplified.append(p.to_dict())
            elif isinstance(p, dict):
                simplified.append(p)
            elif hasattr(p, "__dict__"):
                simplified.append({
                    k: str(v)
                    for k, v in p.__dict__.items()
                    if not k.startswith("_")
                })
            else:
                simplified.append(str(p))

        _collected_profiles.extend(simplified)
        print(f"Added {len(simplified)} profiles (total collected: {len(_collected_profiles)})")
        return simplified

HrFlowProfileWarehouse.write = LocalWriter()

# === Run the Ceipal connector ===
print("⚙️ Fetching profiles from Ceipal...")

result = Ceipal.pull_profile_list(
    workflow_id="ceipal_to_mockai_local",
    action_parameters={"read_mode": "sync"},
    origin_parameters={
        "ceipal_endpoint": "PRODUCTION",
        "api_token": "dfea852be3bdfff393986cd7994e28da98f26f984b32f1962112238017d8635d",
        "limit": 10,
    },
    target_parameters={
        "api_secret": "dummy",
        "api_user": "dummy@example.com",
        "source_key": "dummy_key",
        "only_edit_fields": [],
    },
    connector_name="Ceipal",
)

print(f"Finished Ceipal pull — {len(_collected_profiles)} profiles collected.")

MOCK_AI_URL = "http://localhost:3002/analyze"

if not _collected_profiles:
    print("⚠️  No profiles collected — check Ceipal credentials or endpoint.")
else:
    try:
        with open("ceipal_profiles.json", "w") as f:
            json.dump(_collected_profiles, f, indent=2)
        print(f" Saved {len(_collected_profiles)} profiles to ceipal_profiles.json")
    except Exception as e:
        print("Failed to save profiles:", e)

    try:
        print(f" Sending {len(_collected_profiles)} profiles to Mock AI …")
        resp = requests.post(MOCK_AI_URL, json={"profiles": _collected_profiles})
        print("Mock AI response:", resp.status_code)
        print(resp.text[:400])

        with open("analyzed_profiles.json", "w") as f:
            f.write(resp.text)
        print(" Saved analyzed results to analyzed_profiles.json")
    except Exception as e:
        print("Could not reach Mock AI:", e)

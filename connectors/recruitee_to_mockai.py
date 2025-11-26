import sys, os, json, requests
from collections.abc import Iterable

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "hrflow-connectors/src")))

from hrflow_connectors.v1.connectors.recruitee.connector import Recruitee
from hrflow_connectors.v1.connectors.hrflow.warehouse import HrFlowProfileWarehouse


_collected_profiles = []

class LocalWriter:
    def parameters(self, **kwargs):
        return self

    def __call__(self, profiles, *args, **kwargs):
        global _collected_profiles

        print(f"\n========== LocalWriter.__call__ invoked ==========")
        print(f"profiles type: {type(profiles)}")
        print(f"args: {args}")
        print(f"kwargs keys: {list(kwargs.keys())}")
        
        for key, value in kwargs.items():
            print(f"kwargs['{key}']: type={type(value)}")
            if isinstance(value, list):
                print(f"   → LIST with {len(value)} items!")
                if len(value) > 0:
                    print(f"   → First item type: {type(value[0])}")
        
        for i, arg in enumerate(args):
            print(f"args[{i}]: type={type(arg)}")
            if isinstance(arg, list):
                print(f"   → LIST with {len(arg)} items!")
                if len(arg) > 0:
                    print(f"   → First item type: {type(arg[0])}")

        all_data = []
        
        for param_name in ['profiles', 'data', 'items', 'candidates', 'resumes']:
            if param_name in kwargs and isinstance(kwargs[param_name], list):
                all_data.extend(kwargs[param_name])
                print(f" Found {len(kwargs[param_name])} items in kwargs['{param_name}']")
        
        for arg in args:
            if isinstance(arg, list):
                all_data.extend(arg)
                print(f" Found {len(arg)} items in args")

        print(f" Total items collected: {len(all_data)}")

        simplified = []
        for p in all_data:
            try:
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
            except Exception as e:
                print("Skipping one profile due to:", e)

        _collected_profiles.extend(simplified)
        print(f"Added {len(simplified)} profiles (total: {len(_collected_profiles)})\n")

        return simplified

HrFlowProfileWarehouse.write = LocalWriter()


# === Run the Recruitee connector ===
print("⚙️ Fetching profiles from Recruitee...")

result = Recruitee.pull_profile_list(
    workflow_id="recruitee_to_mockai_local",
    action_parameters={"read_mode": "sync"},
    origin_parameters={
        "company_id": 127297,
        "api_token": "K1NWREw5Szc3MllmRjJGdGkvTHY4dz09",
        "recruitee_endpoint": "PRODUCTION ENDPOINT",
        "limit": 10,
    },
    target_parameters={
        "api_secret": "dummy",
        "api_user": "dummy@example.com",
        "source_key": "dummy_key",
        "only_edit_fields": [],
    },
    connector_name="Recruitee",
)

print("DEBUG → connector result type:", type(result))
if hasattr(result, "data"):
    print("DEBUG → len(result.data):", len(result.data))
elif hasattr(result, "output"):
    print("DEBUG → len(result.output):", len(result.output))
else:
    print("DEBUG → result has no .data or .output attributes")

print(f"Finished Recruitee pull — {len(_collected_profiles)} profiles collected.")

MOCK_AI_URL = "http://localhost:3002/analyze"

if not _collected_profiles:
    print("  No profiles collected — check credentials or endpoint.")
else:
    try:
        with open("recruitee_profiles.json", "w") as f:
            json.dump(_collected_profiles, f, indent=2)
        print(f"Saved {len(_collected_profiles)} profiles to recruitee_profiles.json")
    except Exception as e:
        print("Failed to save profiles:", e)

    try:
        print(f"Sending {len(_collected_profiles)} profiles to Mock AI …")
        resp = requests.post(MOCK_AI_URL, json={"profiles": _collected_profiles})
        print("Mock AI response:", resp.status_code)
        print(resp.text[:400])

        with open("analyzed_profiles.json", "w") as f:
            f.write(resp.text)
        print("Saved analyzed results to analyzed_profiles.json")
    except Exception as e:
        print("Could not reach Mock AI:", e)





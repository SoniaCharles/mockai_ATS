import sys, os, json, requests
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "hrflow-connectors/src")))

from hrflow_connectors.v1.connectors.bamboohr.connector import BambooHR
from hrflow_connectors.v1.connectors.hrflow.warehouse import HrFlowProfileWarehouse, HrFlowJobWarehouse


class LocalWriter:
    def __init__(self, name):
        self.name = name
        self.collected = []

    def parameters(self, **kwargs):
        return self

    def __call__(self, profiles, *args, **kwargs):
        all_data = []
        for key in ["profiles","data","items","candidates","employees","jobs","applicants","applications"]:
            if key in kwargs and isinstance(kwargs[key], list):
                all_data.extend(kwargs[key])
        for arg in args:
            if isinstance(arg, list):
                all_data.extend(arg)
        if isinstance(profiles, list):
            all_data.extend(profiles)
        elif isinstance(profiles, dict):
            all_data.append(profiles)

        simplified = []
        for p in all_data:
            if hasattr(p, "to_dict"):
                simplified.append(p.to_dict())
            elif isinstance(p, dict):
                simplified.append(p)
            elif hasattr(p, "__dict__"):
                simplified.append({k: str(v) for k, v in p.__dict__.items() if not k.startswith("_")})
        self.collected.extend(simplified)
        return []


company_subdomain = os.getenv("BAMBOOHR_SUBDOMAIN", "sonia")
api_key = os.getenv("BAMBOOHR_API_KEY", "53180a4692db2060d2443fe4b56fa401c74565b2")
access_token = os.getenv("ACCESS_TOKEN", "305fa32abcf52d1d791f8d9caaeeb38979eccc3b")
MOCK_AI_URL = "http://localhost:3002/analyze"


def run_profile_connector(action_fn, label):
    writer = LocalWriter(label)
    HrFlowProfileWarehouse.write = writer
    try:
        action_fn(
            workflow_id=f"bamboohr_{label.lower()}",
            action_parameters={"read_mode": "sync"},
            origin_parameters={"company_subdomain": company_subdomain, "access_token": access_token,},
            target_parameters={"api_user": "dummy", "api_secret": "dummy", "source_key": "dummy_key"},
        )
    except Exception as e:
        print(f"Error fetching {label}: {e}")
    print(f"{label}: {len(writer.collected)} records pulled")
    return writer.collected


def run_job_connector(action_fn, label):
    writer = LocalWriter(label)
    HrFlowJobWarehouse.write = writer
    try:
        action_fn(
            workflow_id=f"bamboohr_{label.lower()}",
            action_parameters={"read_mode": "sync"},
            origin_parameters={"company_subdomain": company_subdomain, "access_token": access_token,},
            target_parameters={"api_user": "dummy", "api_secret": "dummy", "board_key": "dummy_board"},
        )
    except Exception as e:
        print(f" Error fetching {label}: {e}")
    print(f"{label}: {len(writer.collected)} records pulled")
    return writer.collected

def update_application_status(company_subdomain, access_token, application_id, status_id):
    url = f"https://{company_subdomain}.bamboohr.com/api/v1/applicant_tracking/applications/{application_id}/status"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    payload = {
        "status": {"id": status_id}
    }

    print(f" Updating BambooHR Application {application_id} → Status {status_id}")
    print(f" POST {url}")

    resp = requests.post(url, json=payload, headers=headers)

    if resp.status_code not in [200, 201]:
        print(f"Failed: {resp.status_code} - {resp.text}")
        return {"success": False, "error": resp.text}

    print(f"Status updated successfully: {resp.text}")
    return {"success": True, "response": resp.json() if resp.text else {}}


print("ACCESS_TOKEN =", os.getenv("ACCESS_TOKEN"))

employees = run_profile_connector(BambooHR.pull_profile_list, "Employees")

try:
    jobs = run_job_connector(BambooHR.pull_job_list, "Jobs")
except AttributeError:
    jobs = []

try:
    applications = run_profile_connector(BambooHR.pull_application_list, "Applications")
except AttributeError:
    applications = []





# === Send to Mock AI ===
payload = {"profiles": employees, "jobs": jobs, "applications": applications}

try:
    print(f"\n Sending {len(employees) + len(jobs) + len(applications)} records to Mock AI...")
    resp = requests.post(MOCK_AI_URL, json=payload)
    resp.raise_for_status()
    analysis = resp.json()

    if "candidates" in analysis:
        print("\n AI Candidate Analysis:\n")
        for c in analysis["candidates"]:
            print(json.dumps(c, indent=2))
    else:
        print("\n Full AI Response:\n", json.dumps(analysis, indent=2))

except Exception as e:
    print(f"❌ Error sending data to Mock AI: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "update_status":
        application_id = int(sys.argv[2])
        status_id = int(sys.argv[3])

        result = update_application_status(
            company_subdomain,
            access_token,
            application_id,
            status_id
        )
        print(json.dumps(result))
        sys.exit(0)

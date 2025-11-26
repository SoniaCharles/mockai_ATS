import sys, os, json, requests

subdomain = os.getenv("WORKABLE_SUBDOMAIN", "techclub-inc")
api_key = os.getenv("WORKABLE_API_KEY", "oHqvHlSpVrbr3AuKRbiqoXRZYWGVlRVRwj3ffDGzpmI")
MOCK_AI_URL = "http://localhost:3002/analyze"


import time

def fetch_workable_jobs():
    url = f"https://{subdomain}.workable.com/spi/v3/jobs"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    retries = 5
    delay = 2

    print("🔍 Fetching jobs from Workable...")

    for attempt in range(retries):
        response = requests.get(url, headers=headers)

        if response.ok:
            jobs = response.json().get("jobs", [])
            print(f"Retrieved {len(jobs)} jobs")
            return jobs

        if response.status_code == 429:
            print(f"⏳ Rate limit hit. Retry {attempt+1}/{retries} in {delay}s...")
            time.sleep(delay)
            delay *= 2
            continue

        print(f"Error fetching jobs: {response.status_code} - {response.text}")
        return []

    print("Could not fetch jobs after retries.")
    return []

def fetch_workable_candidates():
    """Fetch candidates directly from Workable API"""
    url = f"https://{subdomain}.workable.com/spi/v3/candidates?limit=50"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    
    print("🔍 Fetching candidates from Workable...")
    response = requests.get(url, headers=headers)
    
    if not response.ok:
        print(f"Error fetching candidates: {response.status_code} - {response.text}")
        return []
    
    candidates = response.json().get("candidates", [])
    print(f"Retrieved {len(candidates)} candidates")
    
    enriched = []

    for cand in candidates:
        cid = cand.get("id")
        if not cid:
            enriched.append(cand)
            continue

        detail_url = f"{url}/{cid}"
        detail_resp = requests.get(detail_url, headers=headers)

        if detail_resp.ok:
            detail = detail_resp.json().get("candidate", {})
            cand["resume_url"] = detail.get("resume_url")
            cand["experience_entries"] = detail.get("experience_entries")
            cand["education_entries"] = detail.get("education_entries")
            cand["summary"] = detail.get("summary")
            cand["social_profiles"] = detail.get("social_profiles")
        else:
            cand["resume_url"] = None

        enriched.append(cand)

    print("Finished enriching candidates with resume_url")
   
    return enriched


def transform_candidates_to_profiles(candidates):
    profiles = []
    
    for candidate in candidates:
        profile = {
            "id": candidate.get("id"),
            "candidate_id": candidate.get("id"),
            "name": candidate.get("name"),
            "first_name": candidate.get("firstname"),
            "last_name": candidate.get("lastname"),
            "email": candidate.get("email"),
            "phone": candidate.get("phone"),
            "headline": candidate.get("headline"),
            
            "job_id": candidate.get("job", {}).get("shortcode"),
            "job_title": candidate.get("job", {}).get("title"),
            
            "stage": candidate.get("stage"),
            "stage_kind": candidate.get("stage_kind"),
            "disqualified": candidate.get("disqualified", False),
            
            "profile_url": candidate.get("profile_url"),
            "resume_url": candidate.get("resume_url"),
            "sourced": candidate.get("sourced"),
            "created_at": candidate.get("created_at"),
        }
        
        if candidate.get("education_entries"):
            profile["education"] = candidate["education_entries"]
        
        if candidate.get("experience_entries"):
            profile["experience"] = candidate["experience_entries"]
        
        profiles.append(profile)
    
    return profiles


def transform_jobs(jobs):
    transformed = []
    
    for job in jobs:
        job_data = {
            "job_id": job.get("shortcode"),
            "code": job.get("code"),
            "reference": job.get("shortcode"),
            "title": job.get("title"),
            "description": job.get("description"),
            "requirements": job.get("requirements"),
            "benefits": job.get("benefits"),
            "employment_type": job.get("employment_type"),
            "department": job.get("department"),
            "location": job.get("location", {}).get("location_str"),
            "state": job.get("state"),
            "url": job.get("url"),
            "created_at": job.get("created_at"),
        }
        transformed.append(job_data)
    
    return transformed


def create_applications_from_candidates(candidates):
    applications = []
    
    for candidate in candidates:
        job = candidate.get("job", {})
        app = {
            "application_id": candidate.get("id"),
            "candidate_id": candidate.get("id"),
            "job_id": candidate.get("job", {}).get("shortcode"),
            "stage": candidate.get("stage"),
            "stage_kind": candidate.get("stage_kind"),
            "disqualified": candidate.get("disqualified", False),
            "created_at": candidate.get("created_at"),
            "job_title": job.get("title"), 

            "resume_url": candidate.get("resume_url"),
            "profile_url": candidate.get("profile_url"),
        }
        applications.append(app)
    
    return applications


def send_to_mock_ai(profiles, jobs, applications):
    payload = {
        "profiles": profiles,
        "jobs": jobs,
        "applications": applications
    }
    
    total_records = len(profiles) + len(jobs) + len(applications)
    print(f"\n📤 Sending {total_records} records to Mock AI...")
    print(f"   - {len(profiles)} profiles")
    print(f"   - {len(jobs)} jobs")
    print(f"   - {len(applications)} applications")
    
    try:
        resp = requests.post(MOCK_AI_URL, json=payload)
        resp.raise_for_status()
        
        analysis = resp.json()
        print("\nAI Analysis Complete:")
        print(json.dumps(analysis, indent=2))
        
        return analysis
        
    except Exception as e:
        print(f"Error sending to Mock AI: {e}")
        return None


if __name__ == "__main__":
    print("Using Workable:", subdomain)
    print("=" * 60)
    
    # 1: Fetch raw data from Workable
    raw_candidates = fetch_workable_candidates()
    raw_jobs = fetch_workable_jobs()
    
    if not raw_candidates:
        print(" No candidates found. Check your API credentials.")
        exit(1)
    
    # 2: Transform data
    print("\n Transforming data...")
    profiles = transform_candidates_to_profiles(raw_candidates)
    jobs = transform_jobs(raw_jobs)
    applications = create_applications_from_candidates(raw_candidates)
    
    print(f"Transformed:")
    print(f"   - {len(profiles)} profiles")
    print(f"   - {len(jobs)} jobs")
    print(f"   - {len(applications)} applications")
    
    # 3: Save locally for inspection
    with open("workable_data.json", "w") as f:
        json.dump({
            "profiles": profiles,
            "jobs": jobs,
            "applications": applications
        }, f, indent=2)
    print("\nSaved to workable_data.json")
    
    # 4: Send to Mock AI
    print("\n" + "=" * 60)
    analysis = send_to_mock_ai(profiles, jobs, applications)
    
    if analysis and "candidates" in analysis:
        print(f"\n Analyzed {analysis.get('analyzed', 0)} candidates")
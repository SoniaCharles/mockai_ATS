import express from 'express';
import fetch from 'node-fetch';
import dotenv from 'dotenv';
import { exec } from 'child_process';
dotenv.config();

const app = express();
app.use(express.json());

// =================== NANGO CONFIG ===================
const PORT = process.env.PORT || 3002;
const NANGO_BASE_URL = process.env.NANGO_BASE_URL || 'https://api.nango.dev';
const NANGO_SECRET_KEY = process.env.NANGO_SECRET_KEY;
const PROVIDER_CONFIG_KEY = process.env.PROVIDER_CONFIG_KEY || 'recruitee';
const CONNECTION_ID = process.env.CONNECTION_ID;


// =================== HRFLOW CONFIG ===================
const HRFLOW_BASE_URL = process.env.HRFLOW_BASE_URL || 'https://api.hrflow.ai/v1';
const HRFLOW_API_KEY = process.env.HRFLOW_API_KEY;
const HRFLOW_USER_EMAIL = process.env.HRFLOW_USER_EMAIL;
const HRFLOW_SOURCE_KEY = process.env.HRFLOW_SOURCE_KEY;


// Optional HRFlow connector path (Python)
const HRFLOW_CONNECTOR_PATH =
  process.env.HRFLOW_CONNECTOR_PATH ||
  '../connectors/hrflow-connectors/src/hrflow_connectors/v1/connectors/recruitee/connector.py';

// =================== HELPER FUNCTION ===================
async function fetchFromNango(endpoint) {
  const url = `${NANGO_BASE_URL}/proxy/${endpoint}`;
  const resp = await fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${NANGO_SECRET_KEY}`,
      'Provider-Config-Key': PROVIDER_CONFIG_KEY,
      'Connection-Id': CONNECTION_ID,
    },
  });

  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Error fetching ${endpoint}: ${errText}`);
  }

  return await resp.json();
}

// =================== HRFLOW PROFILE UPLOAD ===================
async function sendProfileToHrFlow(profileData) {
  const url = `${HRFLOW_BASE_URL}/profile/indexing`;

  const body = {
    source_key: HRFLOW_SOURCE_KEY,
    profile: {
      info: {
        full_name: profileData.full_name,
        first_name: profileData.full_name?.split(' ')[0] || 'Unknown',
        last_name: profileData.full_name?.split(' ').slice(1).join(' ') || 'Candidate',
        email: profileData.email,
        location: profileData.location || 'Lansing, MI',
        headline: profileData.headline || 'Candidate from Mock AI',
      },
      text: profileData.text || 'Profile created via AI service integration.',
  
      experiences: [
        {
          company: 'Mock AI Generator',
          title: 'AI Candidate Profile',
          start_date: '2023-01-01',
          end_date: '2024-01-01',
          description: 'Auto-generated experience for schema compliance.',
        },
      ],
  
      educations: [
        {
          school: 'AI Generated University',
          degree: 'B.S. Computer Science',
          start_date: '2020-01-01',
          end_date: '2024-01-01',
          description: 'Auto-generated education entry for HrFlow schema.',
        },
      ],
    },
  };
  
  

  
  

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-KEY': HRFLOW_API_KEY,
      'X-USER-EMAIL': HRFLOW_USER_EMAIL,
    },
    body: JSON.stringify(body),
  });

  const data = await response.json();
  if (!response.ok) throw new Error(`HrFlow error: ${data.message || 'Unknown error'}`);
  return data;
}


// =================== HEALTH CHECK ===================
app.get('/health', (req, res) => {
  res.json({ ok: true, message: ' Mock AI ready and listening' });
});

// =================== HRFLOW CANDIDATE FETCH ===================
app.get('/fetch-hrflow-candidates', async (req, res) => {
  console.log('⚙️ Running HRFlow Recruitee connector...');
  exec(`python3 ${HRFLOW_CONNECTOR_PATH}`, (error, stdout, stderr) => {
    if (error) {
      console.error(' HRFlow connector error:', stderr || error.message);
      return res
        .status(500)
        .json({ error: 'Failed to run HRFlow connector', details: stderr });
    }
    // Try to parse JSON output; fallback to text
    try {
      const parsed = JSON.parse(stdout);
      res.json({ total: parsed.length || 0, results: parsed });
    } catch (e) {
      res.json({ raw_output: stdout });
    }
  });
});

// =================== CEIPAL FETCH (Python connector) ===================
app.get('/fetch-ceipal-candidates', async (req, res) => {
  console.log('⚙️ Running HRFlow Ceipal connector...');

  const { exec } = await import('child_process');

  // Call your Ceipal connector
  exec(`python3 ${process.env.HRFLOW_CONNECTOR_PATH}`, (error, stdout, stderr) => {
    if (error) {
      console.error('❌ Ceipal connector error:', stderr || error.message);
      return res
        .status(500)
        .json({ error: 'Failed to run Ceipal connector', details: stderr });
    }

    try {
      const parsed = JSON.parse(stdout);
      console.log(`✅ Retrieved ${parsed.length} profiles from Ceipal`);
      res.json({ total: parsed.length, results: parsed });
    } catch (e) {
      console.warn('⚠️ Non-JSON output from connector, returning raw text');
      res.json({ raw_output: stdout });
    }
  });
});


// =================== CANDIDATE FETCH (Nango) ===================
app.get('/fetch-candidates', async (req, res) => {
  try {
    const url = `${NANGO_BASE_URL}/proxy/candidates`;
    const resp = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${NANGO_SECRET_KEY}`,
        'Provider-Config-Key': PROVIDER_CONFIG_KEY,
        'Connection-Id': CONNECTION_ID,
      },
    });

    if (!resp.ok) {
      const errorText = await resp.text();
      console.error(' Failed to fetch candidates:', errorText);
      return res.status(resp.status).send(errorText);
    }

    const data = await resp.json();
    const enriched = data.candidates.map((c) => {
      let ai_score = Math.floor(Math.random() * 100);
      if (c.source === 'LinkedIn') ai_score += 10;
      if (c.positive_ratings > 50) ai_score += 15;
      if (ai_score > 100) ai_score = 100;

      return {
        name: c.name,
        email: c.emails?.[0],
        source: c.source,
        positive_ratings: c.positive_ratings,
        ai_score,
        recommendation: ai_score > 70 ? 'Highly Recommended' : 'Consider',
      };
    });

    res.json({ total: enriched.length, results: enriched });
  } catch (err) {
    console.error('⚠️ Error:', err);
    res.status(500).json({ error: err.message });
  }
});

// =================== OFFERS FETCH ===================
app.get('/fetch-offers', async (req, res) => {
  try {
    const data = await fetchFromNango('offers');
    res.json({ total: data.meta.total_count, offers: data.offers });
  } catch (err) {
    console.error('Error fetching offers:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// =================== AI ANALYSIS ===================
app.get('/analyze', async (req, res) => {
  try {
    const [candidatesResp, offersResp] = await Promise.all([
      fetchFromNango('candidates'),
      fetchFromNango('offers'),
    ]);

    const candidates = candidatesResp.candidates;
    const offers = offersResp.offers;
    const offerMap = Object.fromEntries(offers.map((o) => [o.id, o]));

    const results = candidates.map((c) => {
      const offer = c.placements?.[0]?.offer_id
        ? offerMap[c.placements[0].offer_id]
        : null;

      let ai_score = Math.floor(Math.random() * 100);
      if (c.source === 'LinkedIn') ai_score += 10;
      if (c.positive_ratings > 50) ai_score += 15;
      if (offer?.education === 'master_degree') ai_score += 5;
      if (ai_score > 100) ai_score = 100;

      return {
        candidate_name: c.name,
        candidate_email: c.emails?.[0],
        source: c.source,
        offer_title: offer?.title || 'N/A',
        employment_type: offer?.employment_type || 'N/A',
        experience_required: offer?.experience || 'N/A',
        ai_score,
        recommendation: ai_score > 70 ? 'Strong Fit' : 'Consider',
      };
    });

    res.json({ analyzed: results.length, results });
  } catch (err) {
    console.error(' Error analyzing data:', err.message);
    res.status(500).json({ error: err.message });
  }
});

app.post("/analyze", async (req, res) => {
  try {
    const profiles = req.body.profiles || [];
    const jobs = req.body.jobs || [];
    const applications = req.body.applications || [];

    console.log(`\n📥 Received ${profiles.length} Employees, ${jobs.length} jobs, ${applications.length} applications`);
    // console.log(JSON.stringify(jobs[0].title.label, null, 2));

    // Build lookup maps
    const jobMap = {};
    for (const job of jobs) {
      const id = job.id || job.job_id || job.JobID || job.code || job.reference;
      jobMap[id] = job;
    }

    const profileMap = {};
    for (const p of profiles) {
      const id = p.id || p.employee_id || p.candidate_id || p.ProfileID;
      profileMap[id] = p;
    }

    // Group applications by job_id
    const jobGroups = {};
    for (const app of applications) {
      const jobId = app.job_id || app.JobID || app.job?.id;
      if (!jobGroups[jobId]) jobGroups[jobId] = [];
      jobGroups[jobId].push(app);
    }

    const analyzed = [];
    for (const [jobId, apps] of Object.entries(jobGroups)) {
      const job = jobMap[jobId] || {};
      const jobName = job.title || job.job_title || job.name || job.job_name || "Unknown Job";
      const JD = job.description || "no description";

      console.log(`Job Title: ${jobName || "Unknown"}, Job ID: ${jobId || "?"}`);
      console.log(`Job Description: ${JD || "Unknown"}`);
      console.log("--------------------------------------------------");

      for (const app of apps) {
        const candidateId = app.candidate_id || app.employee_id || app.ProfileID;
        const candidate = profileMap[candidateId] || app;

        const candidateName =
          candidate.first_name && candidate.last_name
            ? `${candidate.first_name} ${candidate.last_name}`
            : candidate.name || "Unknown Candidate";

        const candidateEmail = candidate.email || candidate.work_email || "N/A";


        // Simple AI mock scoring
        const aiScore = Math.floor(Math.random() * 100);
        const recommendation = aiScore > 70 ? "Strong Fit" : "Consider";
        const application_id = candidate.application_id

        console.log(`Candidate Name: ${candidateName} \nCandidate Email: ${candidateEmail} `);
        console.log(`AI Score: ${aiScore} | (${recommendation})`);
        console.log(`Resume URL: ${candidate.resume_url || "No resume found"}`);
        console.log(`Profile URL: ${candidate.profile_url || "No profile found"}\n`);

        
        if (application_id) {
          let newStatus = 1; // default: NEW
      
          if (aiScore > 70) newStatus = 3;   // Example: Interview
          if (aiScore < 30) newStatus = 5;   // Example: Rejected
      
          fetch("http://localhost:3002/bamboohr/update-status", {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({
                  application_id,
                  status_id: newStatus
              })
          }).then(r => r.json()).then(console.log).catch(console.error);
        } 
        analyzed.push({
          job_id: jobId,
          jobName: jobName,
          candidate: { candidate_id: candidateId, name: candidateName, email: candidateEmail },
          ai_score: aiScore,
          recommendation,
          application_id
        });
      }

      console.log(); // blank line between jobs
    }

    console.log(`Analysis complete for ${analyzed.length} total applicants.\n`);

    res.status(200).json({
      analyzed: analyzed.length,
      grouped_jobs: Object.keys(jobGroups).length,
      candidates: analyzed,
    });
  } catch (err) {
    console.error("❌ Error in POST /analyze:", err);
    res.status(500).json({ error: err.message });
  }
});



// =================== MOCK PROCESS ROUTE ===================
app.post('/process', (req, res) => {
  const { data } = req.body;
  if (!data) return res.status(400).json({ error: 'Missing candidate data' });

  const ai_score = Math.floor(Math.random() * 100);
  const recommendation = ai_score > 70 ? 'Strong Fit' : 'Needs Review';

  res.json({
    candidate: data.name || 'Unknown',
    ai_score,
    recommendation,
    feedback: `AI analysis complete for ${data.name || 'candidate'}.`,
  });
});

// =================== SEND TO HRFLOW ===================
app.post('/send-to-hrflow', async (req, res) => {
  try {
    const { full_name, email, headline, summary, location } = req.body;

    if (!full_name || !email) {
      return res.status(400).json({ error: 'Missing name or email' });
    }

    const result = await sendProfileToHrFlow({
      full_name,
      email,
      headline,
      location,
      text: summary,
    });

    res.json({ success: true, message: 'Profile sent to HrFlow successfully', result });
  } catch (err) {
    console.error('Error sending to HrFlow:', err.message);
    res.status(500).json({ success: false, error: err.message });
  }
});

app.get('/fetch-bamboohr-data', async (req, res) => {
  console.log('⚙️ Running BambooHR → Mock AI integration...');
  const CONNECTOR_PATH = '/Users/apbudget/Desktop/mock-ai/connectors/bamboohr_to_mockai_local.py';

  exec(`python3 ${CONNECTOR_PATH}`, (error, stdout, stderr) => {
    if (error) {
      console.error('❌ BambooHR connector error:', stderr || error.message);
      return res.status(500).json({ error: 'Failed to run BambooHR connector', details: stderr });
    }

    // Try to capture JSON payloads from the connector runner
    try {
      const parsed = JSON.parse(stdout);
      console.log(`✅ Retrieved BambooHR data:`, Object.keys(parsed));
      res.json(parsed);
    } catch {
      console.warn('⚠️ Non-JSON output, returning raw text');
      res.json({ raw_output: stdout });
    }
  });
});

app.get('/auth/bamboohr', (req, res) => {
  const companyDomain = process.env.BAMBOOHR_COMPANY_DOMAIN;
  const clientId = process.env.BAMBOOHR_CLIENT_ID;
  const redirectUri = encodeURIComponent(process.env.BAMBOOHR_REDIRECT_URI);
  const scopes =
    'application+job_opening+email+openid+company_file+employee+employee:contact+employee:education+employee:file+employee:job+employee:name+employee:payroll+employee_directory+offline_access';
  const state = 'test123';

  const authUrl = `https://${companyDomain}.bamboohr.com/authorize.php?request=authorize&response_type=code&client_id=${clientId}&redirect_uri=${redirectUri}&scope=${scopes}&state=${state}`;
  
  console.log('➡️ AUTH URL:', authUrl); // <== Add this line
  res.redirect(authUrl);
});



app.get('/oauth/callback', async (req, res) => {
  const { code } = req.query;
  const companyDomain = process.env.BAMBOOHR_COMPANY_DOMAIN;
  const clientId = process.env.BAMBOOHR_CLIENT_ID;
  const clientSecret = process.env.BAMBOOHR_CLIENT_SECRET;
  const redirectUri = process.env.BAMBOOHR_REDIRECT_URI;

  if (!code) {
    return res.status(400).send('No authorization code found in callback.');
  }

  try {
    const tokenResp = await fetch(`https://${companyDomain}.bamboohr.com/token.php?request=token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_secret: clientSecret,
        client_id: clientId,
        code,
        grant_type: 'authorization_code',
        redirect_uri: redirectUri,
      }),
    });

    const data = await tokenResp.json();

    if (!tokenResp.ok) throw new Error(JSON.stringify(data));

    console.log('✅ OAuth tokens:', data);

    // You can store tokens securely here (DB, env, etc.)
    res.json({
      message: 'OAuth successful!',
      tokens: data,
    });
  } catch (err) {
    console.error('❌ Token exchange failed:', err);
    res.status(500).json({ error: 'Failed to exchange authorization code', details: err.message });
  }
});

app.post('/bamboohr/update-status', async (req, res) => {
  const { application_id, status_id } = req.body;

  if (!application_id || !status_id) {
      return res.status(400).json({ error: "application_id and status_id required" });
  }

  const url = `https://${process.env.BAMBOOHR_COMPANY_DOMAIN}.bamboohr.com/api/v1/applicant_tracking/applications/${application_id}/status`;

  try {
      const response = await fetch(url, {
          method: "POST",
          headers: {
              "Content-Type": "application/json",
              "Accept": "application/json",
              "Authorization": `Bearer ${process.env.ACCESS_TOKEN}`
          },
          body: JSON.stringify({ status_id })
      });

      // BambooHR often returns empty text or "OK", not JSON
      let text = await response.text();

      // Always return valid JSON to your AI-service
      return res.json({
          ok: response.ok,
          http_status: response.status,
          bamboohr_reply: text || "No response body",
          application_id,
          updated_to: status_id
      });

  } catch (err) {
      console.error("❌ BambooHR update error:", err);
      return res.status(500).json({ 
        error: "Failed to update status", 
        details: err.message 
      });
  }
});

app.get('/fetch-workable-data', (req, res) => {
  const PATH = process.env.WORKABLE_CONNECTOR_PATH;

  exec(`python3 ${PATH}`, (error, stdout, stderr) => {
    if (error) {
      console.error("❌ Workable connector error:", stderr || error.message);
      return res.status(500).json({ error: "Workable connector failed", details: stderr });
    }

    try {
      res.json(JSON.parse(stdout));
    } catch {
      res.json({ raw_output: stdout });
    }
  });
});

// =================== START SERVER ===================
app.listen(PORT, () =>
  console.log(` Mock AI running on port ${PORT}`)
);

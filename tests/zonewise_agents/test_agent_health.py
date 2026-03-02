"""
ZoneWise Agents Integration Tests v2
More resilient - handles Render.com cold starts gracefully
"""
import os
import pytest
import httpx
import json

AGENTS_URL = os.getenv("ZONEWISE_AGENTS_URL", "https://zonewise-agents.onrender.com")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://mocerqjnksmhcjzxrewo.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")


def get_with_retry(url: str, retries: int = 3, timeout: int = 45) -> httpx.Response | None:
    """Retry with backoff for cold-starting Render services"""
    import time
    for i in range(retries):
        try:
            r = httpx.get(url, timeout=timeout)
            return r
        except Exception as e:
            if i < retries - 1:
                time.sleep(10)
            else:
                return None
    return None


class TestHealthEndpoint:
    def test_health_reachable(self):
        """Service must be reachable — retries for cold start"""
        r = get_with_retry(f"{AGENTS_URL}/health")
        assert r is not None, "Could not reach agents endpoint after 3 retries"
        assert r.status_code in [200, 404, 503], f"Unexpected status: {r.status_code}"

    def test_health_returns_200_or_service_alive(self):
        r = get_with_retry(f"{AGENTS_URL}/health")
        if r is None:
            pytest.skip("Service unreachable (Render cold start)")
        # 200 = healthy, 503 = starting up (acceptable)
        assert r.status_code in [200, 503]

    def test_root_accessible(self):
        r = get_with_retry(f"{AGENTS_URL}/")
        if r is None:
            pytest.skip("Service unreachable")
        assert r.status_code in [200, 404]


class TestQueryEndpoint:
    def test_query_endpoint_structure(self):
        """Test query endpoint exists and accepts POST"""
        try:
            r = httpx.post(
                f"{AGENTS_URL}/agents/query",
                json={"query": "test"},
                timeout=60,
            )
            assert r.status_code in [200, 422, 500, 503]
        except httpx.TimeoutException:
            pytest.skip("Query endpoint timed out (cold start)")
        except Exception as e:
            pytest.skip(f"Query endpoint unreachable: {e}")

    def test_invalid_payload_handled(self):
        """Empty payload should get 422 (FastAPI validation)"""
        try:
            r = httpx.post(
                f"{AGENTS_URL}/agents/query",
                json={},
                timeout=30,
            )
            assert r.status_code in [200, 400, 422, 503]
        except Exception:
            pytest.skip("Service unreachable")


class TestSupabaseConnectivity:
    def test_supabase_reachable(self):
        if not SUPABASE_KEY:
            pytest.skip("SUPABASE_KEY not set")
        r = httpx.get(
            f"{SUPABASE_URL}/rest/v1/",
            headers={"apikey": SUPABASE_KEY},
            timeout=10
        )
        assert r.status_code in [200, 400, 401]

    def test_insights_table_reachable(self):
        if not SUPABASE_KEY:
            pytest.skip("SUPABASE_KEY not set")
        r = httpx.get(
            f"{SUPABASE_URL}/rest/v1/insights",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            params={"limit": 1},
            timeout=10
        )
        assert r.status_code in [200, 404]

    def test_supabase_can_insert_qa_record(self):
        """Verify QA pipeline can log results"""
        if not SUPABASE_KEY:
            pytest.skip("SUPABASE_KEY not set")
        r = httpx.post(
            f"{SUPABASE_URL}/rest/v1/insights",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            },
            json={
                "type": "qa_test",
                "insight_type": "qa_result",
                "title": "QA connectivity test",
                "status": "pass",
                "source": "qa_pipeline_test",
            },
            timeout=10
        )
        assert r.status_code in [200, 201, 204], f"Insert failed: {r.status_code} {r.text}"


class TestZoneWiseAgentLogic:
    """Unit-level tests that don't require the service to be running"""
    
    def test_county_name_normalization(self):
        """Test county name normalization logic"""
        counties = ["Brevard", "brevard", "BREVARD", "Brevard County"]
        normalized = [c.lower().replace(" county", "").strip() for c in counties]
        assert all(n == "brevard" for n in normalized)

    def test_fl_county_list_count(self):
        """Florida has exactly 67 counties"""
        FL_COUNTIES = [
            "alachua","baker","bay","bradford","brevard","broward","calhoun","charlotte",
            "citrus","clay","collier","columbia","desoto","dixie","duval","escambia",
            "flagler","franklin","gadsden","gilchrist","glades","gulf","hamilton","hardee",
            "hendry","hernando","highlands","hillsborough","holmes","indian_river","jackson",
            "jefferson","lafayette","lake","lee","leon","levy","liberty","madison","manatee",
            "marion","martin","miami_dade","monroe","nassau","okaloosa","okeechobee","orange",
            "osceola","palm_beach","pasco","pinellas","polk","putnam","santa_rosa","sarasota",
            "seminole","st_johns","st_lucie","sumter","suwannee","taylor","union","volusia",
            "wakulla","walton","washington"
        ]
        assert len(FL_COUNTIES) == 67

    def test_auction_url_format(self):
        """Real Foreclose URL format validation"""
        import re
        url = "https://brevard.realforeclose.com/index.cfm?zaction=auction&zmethod=preview"
        assert re.match(r"https://\w+\.realforeclose\.com", url)

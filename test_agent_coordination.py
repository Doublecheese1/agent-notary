import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import agent_coordination


class AgentCoordinationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        os.environ["AGENT_COORDINATION_DB_PATH"] = os.path.join(self.temp.name, "rounds.sqlite3")

    def tearDown(self):
        os.environ.pop("AGENT_COORDINATION_DB_PATH", None)
        self.temp.cleanup()

    def test_extracts_responses_text(self):
        payload = {"output": [{"content": [{"type": "output_text", "text": "hello"}]}]}
        self.assertEqual(agent_coordination._extract_text(payload), "hello")

    async def test_two_models_review_each_other_and_store_joint_result(self):
        replies = ["openai first", "grok first", "openai review", "grok review", "joint result"]
        with patch.object(agent_coordination, "_ask", new=AsyncMock(side_effect=replies)) as ask:
            result = await agent_coordination.coordinate(
                agent_coordination.CoordinationRequest(task="Coordinate outreach ownership")
            )
        self.assertEqual(ask.await_count, 5)
        self.assertEqual(result["joint_decision"], "joint result")
        self.assertEqual(result["status"], "complete")
        with agent_coordination._database() as db:
            row = db.execute("SELECT * FROM agent_rounds WHERE id=?", (result["id"],)).fetchone()
        self.assertEqual(row["openai_review"], "openai review")
        self.assertEqual(row["xai_review"], "grok review")


if __name__ == "__main__":
    unittest.main()

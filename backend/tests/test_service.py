from pathlib import Path

from backend.app.config import Settings
from backend.app.corpus import load_corpus
from backend.app.service import PlantKnowledgeService


PROJECT = Path(__file__).resolve().parents[2]


def make_settings(**kwargs):
    base = Settings(data_file=PROJECT / "data" / "plants.jsonl")
    values = base.__dict__ | kwargs
    return Settings(**values)


def test_seed_corpus_loads_unique_documents():
    docs = load_corpus(PROJECT / "data" / "plants.jsonl")
    assert len(docs) >= 4
    assert len({doc.document_id for doc in docs}) == len(docs)


def test_search_finds_plant_by_name_and_alias():
    service = PlantKnowledgeService(make_settings())
    assert service.search("Dionaea muscipula", 5)[0]["document_id"] == "plant-dionaea-001"
    assert service.search("кувшиночник", 5)[0]["document_id"] == "plant-nepenthes-001"


def test_ask_returns_retrieval_only_when_llm_is_not_configured():
    service = PlantKnowledgeService(make_settings(llm_provider="none"))
    result = service.ask("венерина мухоловка ловушка створки")
    assert result["status"] == "answered"
    assert result["generation_mode"] == "retrieval_only"
    assert result["sources"]
    assert "без генеративного пересказа" in result["answer"]


def test_ask_abstains_on_question_outside_corpus():
    service = PlantKnowledgeService(make_settings(llm_provider="none"))
    result = service.ask("Какое комнатное растение лечит диабет?")
    assert result["status"] == "insufficient_data"
    assert result["sources"] == []


class FakeLLM:
    def __init__(self):
        self.calls = 0

    def chat(self, messages, tools=None):
        self.calls += 1
        if self.calls == 1:
            assert tools
            return {"tool_calls": [{
                "id": "call-1",
                "type": "function",
                "function": {"name": "search_plant_knowledge", "arguments": '{"query":"непентес кувшин"}'},
            }]}
        tool_message = next(m for m in reversed(messages) if m["role"] == "tool")
        assert "source_ref" in tool_message["content"]
        return {"content": "Непентес образует кувшинчатые ловушки [S2]."}


def test_agent_can_call_search_tool_and_receives_source_refs():
    settings = make_settings(llm_provider="ollama", agent_max_tool_calls=2)
    service = PlantKnowledgeService(settings)
    fake = FakeLLM()
    service.llm = fake
    result = service.ask("Что известно о хищных ловушках растений?", agentic=True)
    assert result["generation_mode"] == "agentic_rag"
    assert result["retrieval"]["tool_calls"] == 1
    assert "[S2]" in result["answer"]
    assert len(result["sources"]) >= 1


class BudgetLLM:
    def __init__(self):
        self.calls = 0

    def chat(self, messages, tools=None):
        self.calls += 1
        if self.calls == 1:
            assert tools is not None
            return {"tool_calls": [{
                "id": "budget-call-1",
                "type": "function",
                "function": {"name": "search_plant_knowledge", "arguments": '{"query":"непентес кувшин"}'},
            }]}
        assert tools is None, "tools must be removed after reaching the call budget"
        return {"content": "В имеющихся материалах описаны кувшинчатые ловушки непентеса [S1]."}


def test_agent_removes_tools_after_call_budget_is_reached():
    service = PlantKnowledgeService(make_settings(llm_provider="ollama", agent_max_tool_calls=1))
    fake = BudgetLLM()
    service.llm = fake
    result = service.ask("Опиши хищные ловушки растений", agentic=True)
    assert fake.calls == 2
    assert result["retrieval"]["tool_calls"] == 1
    assert result["generation_mode"] == "agentic_rag"


class PersistentToolLLM:
    """Simulates a model that ignores the server's disabled-tools signal."""
    def __init__(self):
        self.calls = 0

    def chat(self, messages, tools=None):
        self.calls += 1
        if self.calls == 1:
            assert tools is not None
        else:
            assert tools is None
        return {"tool_calls": [{
            "id": f"ignored-tools-{self.calls}",
            "type": "function",
            "function": {"name": "search_plant_knowledge", "arguments": '{"query":"непентес кувшин"}'},
        }]}

def test_agent_stops_if_model_requests_tools_after_budget_is_exhausted():
    service = PlantKnowledgeService(make_settings(llm_provider="ollama", agent_max_tool_calls=1))
    fake = PersistentToolLLM()
    service.llm = fake
    result = service.ask("Расскажи о венериной мухоловке", agentic=True)
    assert fake.calls == 2
    assert result["generation_mode"] == "retrieval_only"
    assert result["retrieval"]["tool_calls"] == 1
    assert result["sources"]

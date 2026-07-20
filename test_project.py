import pytest
from unittest.mock import patch
import io
from project import (
    verify_files,
    sort,
    decode,
    get_llm_fields,
    write_report,
)
from classes import (
    Event_Start,
    Event_End,
    LLM_Start,
    LLM_End,
    Event_Error,
    Logger_Warning,
)


def test_verify_files():

    with patch(
        "sys.argv", ["project.py", "--input", "input.py", "--output", "output.txt"]
    ):
        with pytest.raises(SystemExit):
            verify_files()

    with patch(
        "sys.argv", ["project.py", "--input", "input.txt", "--output", "output.csv"]
    ):
        with pytest.raises(SystemExit):
            verify_files()

    with patch(
        "sys.argv", ["project.py", "--iput", "input.txt", "--output", "output.txt"]
    ):
        with pytest.raises(SystemExit):
            verify_files()

    with patch(
        "sys.argv", ["project.py", "--input", "input.txt", "-output", "output.txt"]
    ):
        with pytest.raises(SystemExit):
            verify_files()

    with patch("sys.argv", ["project.py", "input.txt", "--output", "output.txt"]):
        with pytest.raises(SystemExit):
            verify_files()

    with patch("sys.argv", ["project.py", "--input", "--output", "output.txt"]):
        with pytest.raises(SystemExit):
            verify_files()

    with patch("sys.argv", ["project.py", "--input", "input.txt", "output.txt"]):
        with pytest.raises(SystemExit):
            verify_files()

    with patch("sys.argv", ["project.py", "--input", "input.txt", "--output"]):
        with pytest.raises(SystemExit):
            verify_files()

    with patch("sys.argv", ["project.py", "--input", "input.txt", "--output", "output.txt", "inoutput.txt"]):
        with pytest.raises(SystemExit):
            verify_files()

    with patch(
        "sys.argv", ["project.py", "--input", "input.txt", "--output", "output.txt"]
    ):
        with patch("os.path.exists", return_value=False):
            with pytest.raises(SystemExit):
                verify_files()

    with patch(
        "sys.argv", ["project.py", "--input", "input.txt", "--output", "output.txt"]
    ):
        with patch("os.path.exists", side_effect=lambda file: file == "input.txt"):
            response = verify_files()
            assert response.input == "input.txt"
            assert response.output == "output.txt"

    with patch(
        "sys.argv", ["project.py", "--input", "input.txt", "--output", "output.txt"]
    ):
        with patch("os.path.exists", return_value=True):
            with patch("builtins.input", return_value="Y"):
                response = verify_files()
                assert response.input == "input.txt"
                assert response.output == "output.txt"

    with patch(
        "sys.argv", ["project.py", "--input", "input.txt", "--output", "output.txt"]
    ):
        with patch("os.path.exists", return_value=True):
            with patch("builtins.input", return_value="y"):
                response = verify_files()
                assert response.input == "input.txt"
                assert response.output == "output.txt"

    with patch(
        "sys.argv", ["project.py", "--input", "input.txt", "--output", "output.txt"]
    ):
        with patch("os.path.exists", return_value=True):
            with patch("builtins.input", side_effect=["n", "new_output.txt", "Y"]):
                response = verify_files()
                assert response.input == "input.txt"
                assert response.output == "new_output.txt"

    with patch(
        "sys.argv", ["project.py", "--input", "input.txt", "--output", "output.txt"]
    ):
        with patch("os.path.exists", return_value=[True]):
            with patch("builtins.input", side_effect=["X", "N", "new_output.txt", "Y"]):
                response = verify_files()
                assert response.input == "input.txt"
                assert response.output == "new_output.txt"


def test_sort():

    starts_stack = {}

    event = sort(
        "chain/start",
        '[chain:LangGraph] Entering Chain run with input:\n{"messages": [{"role": "user", "content": "What is 25 raised to the power of 0.5?"}]}',
        starts_stack,
    )
    assert event.type == "chain"
    assert event.breadcrumbs == "chain:LangGraph"
    assert event.phase == "start"
    assert event.input_data == {
        "messages": [
            {"role": "user", "content": "What is 25 raised to the power of 0.5?"}
        ]
    }

    event = sort(
        "tool/end",
        "[chain:LangGraph > chain:tools > tool:calculator] [3ms] Exiting Tool run with output:\n\"content='5.0' name='calculator' tool_call_id='ac68455b-7cea-4d7d-a602-c3d19fa1ce26'\"",
        starts_stack,
    )
    assert event.type == "tool"
    assert event.breadcrumbs == "chain:LangGraph > chain:tools > tool:calculator"
    assert event.phase == "end"
    assert event.duration == "3ms"
    assert (
        event.output_data
        == "\"content='5.0' name='calculator' tool_call_id='ac68455b-7cea-4d7d-a602-c3d19fa1ce26'\""
    )

    event = sort(
        "llm/start",
        '[chain:LangGraph > chain:model > llm:ChatOllama] Entering LLM run with input:{"prompts": ["Human: What is 25 raised to the power of 0.5?"]}',
        starts_stack,
    )
    assert event.type == "llm"
    assert event.breadcrumbs == "chain:LangGraph > chain:model > llm:ChatOllama"
    assert event.phase == "start"
    assert event.prompts == ["Human: What is 25 raised to the power of 0.5?"]
    assert starts_stack == {"chain:LangGraph > chain:model > llm:ChatOllama": [event]}

    event = sort(
        "llm/end",
        '[chain:LangGraph > chain:model > llm:ChatOllama] [6.25s] Exiting LLM run with output:\n{"generations": [[{"text": "", "generation_info": {"model": "llama3.2", "created_at": "2026-07-10T21:00:34.33193Z", "done": true, "done_reason": "stop", "total_duration": 6221429709, "load_duration": 4765148209, "prompt_eval_count": 172, "prompt_eval_duration": 648610000, "eval_count": 20, "eval_duration": 787932000, "logprobs": null, "model_name": "llama3.2", "model_provider": "ollama"}, "type": "ChatGeneration", "message": {"lc": 1, "type": "constructor", "id": ["langchain", "schema", "messages", "AIMessage"], "kwargs": {"content": "", "response_metadata": {"model": "llama3.2", "created_at": "2026-07-10T21:00:34.33193Z", "done": true, "done_reason": "stop", "total_duration": 6221429709, "load_duration": 4765148209, "prompt_eval_count": 172, "prompt_eval_duration": 648610000, "eval_count": 20, "eval_duration": 787932000, "logprobs": null, "model_name": "llama3.2", "model_provider": "ollama"}, "type": "ai", "id": "lc_run--019f4dd4-ee3a-7760-b2ef-aa7b364eb274-0", "tool_calls": [{"name": "calculator", "args": {"expression": "25**0.5"}, "id": "ac68455b-7cea-4d7d-a602-c3d19fa1ce26", "type": "tool_call"}], "usage_metadata": {"input_tokens": 172, "output_tokens": 20, "total_tokens": 192}, "invalid_tool_calls": []}}}]], "llm_output": null, "run": null, "type": "LLMResult"}',
        starts_stack,
    )
    assert event.type == "llm"
    assert event.breadcrumbs == "chain:LangGraph > chain:model > llm:ChatOllama"
    assert event.phase == "end"
    assert event.duration == "6.25s"
    assert event.llm_fields == {
        "Prompt 1": {
            "Prompt Content": "Human: What is 25 raised to the power of 0.5?",
            "Candidate Responses": {
                "Candidate Response 1": {
                    "content": "",
                    "token_usage": {
                        "input_tokens": 172,
                        "output_tokens": 20,
                        "total_tokens": 192,
                    },
                    "tool_calls": [
                        {
                            "name": "calculator",
                            "args": {"expression": "25**0.5"},
                            "id": "ac68455b-7cea-4d7d-a602-c3d19fa1ce26",
                            "type": "tool_call",
                        }
                    ],
                    "done_reason": "stop",
                }
            },
        }
    }

    event = sort(
        "chain/error",
        '[chain:LangGraph > chain:tools] [320ms] Chain run errored with error:\n"ImportError(\'cosine_similarity requires numpy to be installed. Please install numpy with `pip install numpy`.\')Traceback (most recent call last):\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langgraph/_internal/_runnable.py", line 684, in invoke\n    input = context.run(step.invoke, input, config, **kwargs)\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langgraph/_internal/_runnable.py", line 426, in invoke\n    ret = self.func(*args, **kwargs)\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langgraph/prebuilt/tool_node.py", line 822, in _func\n    outputs = list(\n        executor.map(self._run_one, tool_calls, input_types, tool_runtimes)\n    )\n\n\n  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/concurrent/futures/_base.py", line 645, in result_iterator\n    yield _result_or_cancel(fs.pop())\n          ~~~~~~~~~~~~~~~~~^^^^^^^^^^\n\n\n  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/concurrent/futures/_base.py", line 312, in _result_or_cancel\n    return fut.result(timeout)\n           ~~~~~~~~~~^^^^^^^^^\n\n\n  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/concurrent/futures/_base.py", line 454, in result\n    return self.__get_result()\n           ~~~~~~~~~~~~~~~~~^^\n\n\n  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/concurrent/futures/_base.py", line 396, in __get_result\n    raise self._exception\n\n\n  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/concurrent/futures/thread.py", line 86, in run\n    result = ctx.run(self.task)\n\n\n  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/concurrent/futures/thread.py", line 73, in run\n    return fn(*args, **kwargs)\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langchain_core/runnables/config.py", line 650, in _wrapped_fn\n    return contexts.pop().run(fn, *args)\n           ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langgraph/prebuilt/tool_node.py", line 1046, in _run_one\n    return self._execute_tool_sync(tool_request, input_type, config)\n           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langgraph/prebuilt/tool_node.py", line 1006, in _execute_tool_sync\n    content = _handle_tool_error(e, flag=self._handle_tool_errors)\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langgraph/prebuilt/tool_node.py", line 434, in _handle_tool_error\n    content = flag(e)  # type: ignore [assignment, call-arg]\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langgraph/prebuilt/tool_node.py", line 391, in _default_handle_tool_errors\n    raise e\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langgraph/prebuilt/tool_node.py", line 958, in _execute_tool_sync\n    response = tool.invoke(call_args, config)\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langchain_core/tools/base.py", line 738, in invoke\n    return self.run(tool_input, **kwargs)\n           ~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langchain_core/tools/base.py", line 1100, in run\n    raise error_to_raise\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langchain_core/tools/base.py", line 1066, in run\n    response = context.run(self._run, *tool_args, **tool_kwargs)\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langchain_core/tools/structured.py", line 97, in _run\n    return self.func(*args, **kwargs)\n           ~~~~~~~~~^^^^^^^^^^^^^^^^^\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langchain_core/tools/retriever.py", line 68, in func\n    docs = retriever.invoke(query, config={"callbacks": callbacks})\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langchain_core/retrievers.py", line 222, in invoke\n    result = self._get_relevant_documents(\n        input, run_manager=run_manager, **kwargs_\n    )\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langchain_core/vectorstores/base.py", line 1045, in _get_relevant_documents\n    docs = self.vectorstore.similarity_search(query, **kwargs_)\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langchain_core/vectorstores/in_memory.py", line 407, in similarity_search\n    return [doc for doc, _ in self.similarity_search_with_score(query, k, **kwargs)]\n                              ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langchain_core/vectorstores/in_memory.py", line 366, in similarity_search_with_score\n    return self.similarity_search_with_score_by_vector(\n           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^\n        embedding,\n        ^^^^^^^^^^\n        k,\n        ^^\n        **kwargs,\n        ^^^^^^^^^\n    )\n    ^\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langchain_core/vectorstores/in_memory.py", line 353, in similarity_search_with_score_by_vector\n    for doc, similarity, _ in self._similarity_search_with_score_by_vector(\n                              ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^\n        embedding=embedding, k=k, filter=filter\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n    )\n    ^\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langchain_core/vectorstores/in_memory.py", line 314, in _similarity_search_with_score_by_vector\n    similarity = cosine_similarity([embedding], [doc["vector"] for doc in docs])[0]\n                 ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\n\n  File "/Users/jacob/Desktop/AI Security/CS50P/Final Project/venv/lib/python3.14/site-packages/langchain_core/vectorstores/utils.py", line 59, in _cosine_similarity\n    raise ImportError(msg)\n\n\nImportError: cosine_similarity requires numpy to be installed. Please install numpy with `pip install numpy`.',
        starts_stack,
    )
    assert event.name == "ImportError"
    assert event.type == "chain"
    assert event.breadcrumbs == "chain:LangGraph > chain:tools"
    assert event.phase == "error"
    assert event.duration == "320ms"
    assert (
        event.message
        == "cosine_similarity requires numpy to be installed. Please install numpy with `pip install numpy`."
    )

    event = sort(
        "Error in ConsoleCallbackHandler.on_tool_start callback: KeyError('input')",
        "",
        starts_stack,
    )
    assert event.name == "KeyError"
    assert event.handler == "ConsoleCallbackHandler"
    assert event.method == "on_tool_start"
    assert event.message == "input"

    starts_stack = {}

    event = sort("chain/start", "", {},)
    assert event.type == "chain"
    assert event.breadcrumbs == None
    assert event.phase == "start"
    assert event.input_data == None

    event = sort("tool/end", "", {},)
    assert event.type == "tool"
    assert event.breadcrumbs == None
    assert event.phase == "end"
    assert event.duration == None
    assert event.output_data == None

    event = sort("llm/start", "", {},)
    assert event.type == "llm"
    assert event.breadcrumbs == None
    assert event.phase == "start"
    assert event.prompts == []
    assert starts_stack == {}

    event = sort("llm/end", "", {},)
    assert event.type == "llm"
    assert event.breadcrumbs == None
    assert event.phase == "end"
    assert event.duration == None
    assert event.llm_fields == {}

    event = sort("chain/error", "", {},)
    assert event.name == None
    assert event.type == "chain"
    assert event.breadcrumbs == None
    assert event.phase == "error"
    assert event.duration == None
    assert event.message == None

    event = sort("Error in hello world", "", {})
    assert event.name == None
    assert event.handler == None
    assert event.method == None
    assert event.message == None

    assert sort("", "", {},) == None


def test_decode():

    assert decode(
        "[chain:LangGraph > chain:model > llm:ChatOllama] Entering LLM run with input:{\"prompts\": [\"Human: What is 25 raised to the power of 0.5?\\nAI: [{'name': 'calculator', 'args': {'expression': '25**0.5'}, 'id': 'ac68455b-7cea-4d7d-a602-c3d19fa1ce26', 'type': 'tool_call'}]\\nTool: 5.0\"]}"
    ) == {
        "prompts": [
            "Human: What is 25 raised to the power of 0.5?\nAI: [{'name': 'calculator', 'args': {'expression': '25**0.5'}, 'id': 'ac68455b-7cea-4d7d-a602-c3d19fa1ce26', 'type': 'tool_call'}]\nTool: 5.0"
        ]
    }
    assert decode("hello, world") == None
    assert decode("{hello: world}") == None


def test_get_llm_fields():

    llm_start = LLM_Start(
        "llm",
        "chain:LangGraph > chain:model > llm:ChatOllama",
        ["Human: When was the Eiffel Tower completed?"],
    )

    assert get_llm_fields(
        {
            "generations": [
                [
                    {
                        "text": "",
                        "generation_info": {
                            "model": "llama3.2",
                            "created_at": "2026-07-14T13:44:27.468018Z",
                            "done": True,
                            "done_reason": "stop",
                            "total_duration": 3780086625,
                            "load_duration": 231793708,
                            "prompt_eval_count": 173,
                            "prompt_eval_duration": 2422005000,
                            "eval_count": 23,
                            "eval_duration": 1003205000,
                            "logprobs": None,
                            "model_name": "llama3.2",
                            "model_provider": "ollama",
                        },
                        "type": "ChatGeneration",
                        "message": {
                            "lc": 1,
                            "type": "constructor",
                            "id": ["langchain", "schema", "messages", "AIMessage"],
                            "kwargs": {
                                "content": "",
                                "response_metadata": {
                                    "model": "llama3.2",
                                    "created_at": "2026-07-14T13:44:27.468018Z",
                                    "done": True,
                                    "done_reason": "stop",
                                    "total_duration": 3780086625,
                                    "load_duration": 231793708,
                                    "prompt_eval_count": 173,
                                    "prompt_eval_duration": 2422005000,
                                    "eval_count": 23,
                                    "eval_duration": 1003205000,
                                    "logprobs": None,
                                    "model_name": "llama3.2",
                                    "model_provider": "ollama",
                                },
                                "type": "ai",
                                "id": "lc_run--019f60df-2181-7691-accd-003773e4a42f-0",
                                "tool_calls": [
                                    {
                                        "name": "search_facts",
                                        "args": {
                                            "query": "Eiffel Tower completion date"
                                        },
                                        "id": "0b73cf64-43b2-4392-9a34-9399a4364f74",
                                        "type": "tool_call",
                                    }
                                ],
                                "usage_metadata": {
                                    "input_tokens": 173,
                                    "output_tokens": 23,
                                    "total_tokens": 196,
                                },
                                "invalid_tool_calls": [],
                            },
                        },
                    }
                ]
            ],
            "llm_output": None,
            "run": None,
            "type": "LLMResult",
        },
        llm_start,
    ) == {
        "Prompt 1": {
            "Prompt Content": "Human: When was the Eiffel Tower completed?",
            "Candidate Responses": {
                "Candidate Response 1": {
                    "content": "",
                    "token_usage": {
                        "input_tokens": 173,
                        "output_tokens": 23,
                        "total_tokens": 196,
                    },
                    "tool_calls": [
                        {
                            "name": "search_facts",
                            "args": {"query": "Eiffel Tower completion date"},
                            "id": "0b73cf64-43b2-4392-9a34-9399a4364f74",
                            "type": "tool_call",
                        }
                    ],
                    "done_reason": "stop",
                }
            },
        }
    }

    assert get_llm_fields(
        {
            "generations": [
                [
                    {
                        "text": "",
                        "generation_info": {
                            "model": "llama3.2",
                            "created_at": "2026-07-14T13:44:27.468018Z",
                            "done": True,
                            "done_reason": "stop",
                            "total_duration": 3780086625,
                            "load_duration": 231793708,
                            "prompt_eval_count": 173,
                            "prompt_eval_duration": 2422005000,
                            "eval_count": 23,
                            "eval_duration": 1003205000,
                            "logprobs": None,
                            "model_name": "llama3.2",
                            "model_provider": "ollama",
                        },
                        "type": "ChatGeneration",
                        "message": {
                            "lc": 1,
                            "type": "constructor",
                            "id": ["langchain", "schema", "messages", "AIMessage"],
                            "kwargs": {
                                "content": "",
                                "response_metadata": {
                                    "model": "llama3.2",
                                    "created_at": "2026-07-14T13:44:27.468018Z",
                                    "done": True,
                                    "done_reason": "stop",
                                    "total_duration": 3780086625,
                                    "load_duration": 231793708,
                                    "prompt_eval_count": 173,
                                    "prompt_eval_duration": 2422005000,
                                    "eval_count": 23,
                                    "eval_duration": 1003205000,
                                    "logprobs": None,
                                    "model_name": "llama3.2",
                                    "model_provider": "ollama",
                                },
                                "type": "ai",
                                "id": "lc_run--019f60df-2181-7691-accd-003773e4a42f-0",
                                "tool_calls": [
                                    {
                                        "name": "search_facts",
                                        "args": {
                                            "query": "Eiffel Tower completion date"
                                        },
                                        "id": "0b73cf64-43b2-4392-9a34-9399a4364f74",
                                        "type": "tool_call",
                                    }
                                ],
                                "usage_metadata": {
                                    "input_tokens": 173,
                                    "output_tokens": 23,
                                    "total_tokens": 196,
                                },
                                "invalid_tool_calls": [],
                            },
                        },
                    }
                ]
            ],
            "llm_output": None,
            "run": None,
            "type": "LLMResult",
        },
        None,
    ) == {
        "Prompt 1": {
            "Prompt Content": None,
            "Candidate Responses": {
                "Candidate Response 1": {
                    "content": "",
                    "token_usage": {
                        "input_tokens": 173,
                        "output_tokens": 23,
                        "total_tokens": 196,
                    },
                    "tool_calls": [
                        {
                            "name": "search_facts",
                            "args": {"query": "Eiffel Tower completion date"},
                            "id": "0b73cf64-43b2-4392-9a34-9399a4364f74",
                            "type": "tool_call",
                        }
                    ],
                    "done_reason": "stop",
                }
            },
        }
    }

    assert get_llm_fields(None, None) == {}
    assert get_llm_fields(None, llm_start) == {}
    assert get_llm_fields("hello, world", None) == {}
    assert get_llm_fields("hello, world", llm_start) == {}
    assert get_llm_fields({"hello: world"}, llm_start) == {}


def test_write_report():

    event_start = Event_Start(
        "chain",
        "chain:LangGraph > chain:tools",
        {
            "input": [
                {
                    "name": "search_facts",
                    "args": {"query": "Eiffel Tower completion date"},
                    "id": "9d4436a9-3478-4167-a6ef-716929246cd5",
                    "type": "tool_call",
                }
            ]
        },
    )

    event_end = Event_End(
        "tool",
        "chain:LangGraph > chain:tools > tool:search_facts",
        "864ms",
        "content='The Eiffel Tower was completed in 1889.\n\nThe capital of France is Paris.\n\nPython is a popular programming language.' name='search_facts' tool_call_id='9d4436a9-3478-4167-a6ef-716929246cd5'",
    )

    llm_start = LLM_Start(
        "llm",
        "chain:LangGraph > chain:model > llm:ChatOllama",
        [
            "Human: When was the Eiffel Tower completed?\nAI: [{'name': 'search_facts', 'args': {'query': 'Eiffel Tower completion date'}, 'id': '9d4436a9-3478-4167-a6ef-716929246cd5', 'type': 'tool_call'}]\nTool: The Eiffel Tower was completed in 1889.\n\nThe capital of France is Paris.\n\nPython is a popular programming language."
        ],
    )

    llm_end = LLM_End(
        "llm",
        "chain:LangGraph > chain:model > llm:ChatOllama",
        "2.30s",
        {
            "Prompt 1": {
                "Prompt Content": "Human: When was the Eiffel Tower completed?\nAI: [{'name': 'search_facts', 'args': {'query': 'Eiffel Tower completion date'}, 'id': '9d4436a9-3478-4167-a6ef-716929246cd5', 'type': 'tool_call'}]\nTool: The Eiffel Tower was completed in 1889.\n\nThe capital of France is Paris.\n\nPython is a popular programming language.",
                "Candidate Responses": {
                    "Candidate Response 1": {
                        "content": "It seems like I provided some extra information that wasn't directly related to the original question. Let me try again with just the relevant response:\n\nThe Eiffel Tower was completed in 1889.",
                        "token_usage": {
                            "input_tokens": 124,
                            "output_tokens": 41,
                            "total_tokens": 165,
                        },
                        "tool_calls": [],
                        "done_reason": "stop",
                    }
                },
            }
        },
        llm_start,
    )

    event_error = Event_Error(
        "ImportError",
        "tool",
        "chain:LangGraph > chain:tools > tool:search_facts",
        "310ms",
        "cosine_similarity requires numpy to be installed. Please install numpy with `pip install numpy`.",
    )

    logger_warning = Logger_Warning(
        "KeyError", "ConsoleCallbackHandler", "on_tool_start", "input"
    )

    output = io.StringIO()
    write_report(6, output, event_start)
    assert (
        output.getvalue()
        == "    Event #6: Chain Start\n        Breadcrumbs: chain:LangGraph > chain:tools\n        Input: {'input': [{'name': 'search_facts', 'args': {'query': 'Eiffel Tower completion date'}, 'id': '9d4436a9-3478-4167-a6ef-716929246cd5', 'type': 'tool_call'}]}\n\n"
    )

    output = io.StringIO()
    write_report(8, output, event_end)
    assert (
        output.getvalue()
        == "        Event #8: Tool End\n            Breadcrumbs: chain:LangGraph > chain:tools > tool:search_facts\n            Duration: 864ms\n            Output: content='The Eiffel Tower was completed in 1889. →  → The capital of France is Paris. →  → Python is a popular programming language.' name='search_facts' tool_call_id='9d4436a9-3478-4167-a6ef-716929246cd5'\n\n"
    )

    output = io.StringIO()
    write_report(11, output, llm_start)
    assert (
        output.getvalue()
        == "        Event #11: LLM Start\n            Breadcrumbs: chain:LangGraph > chain:model > llm:ChatOllama\n            LLM Prompts:\n                 Prompt 1: Human: When was the Eiffel Tower completed? → AI: [{'name': 'search_facts', 'args': {'query': 'Eiffel Tower completion date'}, 'id': '9d4436a9-3478-4167-a6ef-716929246cd5', 'type': 'tool_call'}] → Tool: The Eiffel Tower was completed in 1889. →  → The capital of France is Paris. →  → Python is a popular programming language.\n\n"
    )

    output = io.StringIO()
    write_report(12, output, llm_end)
    assert (
        output.getvalue()
        == "        Event #12: LLM End\n            Breadcrumbs: chain:LangGraph > chain:model > llm:ChatOllama\n            Duration: 2.30s\n            Key Outputs:\n                Prompt 1: Human: When was the Eiffel Tower completed? → AI: [{'name': 'search_facts', 'args': {'query': 'Eiffel Tower completion date'}, 'id': '9d4436a9-3478-4167-a6ef-716929246cd5', 'type': 'tool_call'}] → Tool: The Eiffel Tower was completed in 1889. →  → The capital of France is Paris. →  → Python is a popular programming language.\n                    Candidate Response 1:\n                        content: It seems like I provided some extra information that wasn't directly related to the original question. Let me try again with just the relevant response: →  → The Eiffel Tower was completed in 1889.\n                        token_usage: {'input_tokens': 124, 'output_tokens': 41, 'total_tokens': 165}\n                        tool_calls: N/A\n                        done_reason: stop\n\n"
    )

    output = io.StringIO()
    write_report(8, output, event_error)
    assert (
        output.getvalue()
        == "        Event #8: Tool Error\n            Error Type: ImportError\n            Breadcrumbs: chain:LangGraph > chain:tools > tool:search_facts\n            Duration: 310ms\n            Error Message: cosine_similarity requires numpy to be installed. Please install numpy with `pip install numpy`.\n\n"
    )

    output = io.StringIO()
    write_report(7, output, logger_warning)
    assert (
        output.getvalue()
        == "Event #7: KeyError\n    Handler Class: ConsoleCallbackHandler\n    Method Name: on_tool_start\n    Error Message: input\n\n"
    )

    event_start = Event_Start("chain", None, None,)

    event_end = Event_End("tool", None, None, None,)

    llm_start = LLM_Start("llm", None, [],)

    llm_end = LLM_End("llm", None, None, {}, None,)

    event_error = Event_Error(None, "tool", None, None, None,)

    logger_warning = Logger_Warning(None, None, None, None)

    output = io.StringIO()
    write_report(6, output, event_start)
    assert (
        output.getvalue()
        == "Event #6: Chain Start\n    Breadcrumbs: N/A\n    Input: N/A\n\n"
    )

    output = io.StringIO()
    write_report(8, output, event_end)
    assert (
        output.getvalue()
        == "Event #8: Tool End\n    Breadcrumbs: N/A\n    Duration: N/A\n    Output: N/A\n\n"
    )

    output = io.StringIO()
    write_report(11, output, llm_start)
    assert (
        output.getvalue()
        == "Event #11: LLM Start\n    Breadcrumbs: N/A\n    LLM Prompts: N/A\n\n"
    )

    output = io.StringIO()
    write_report(12, output, llm_end)
    assert (
        output.getvalue()
        == "Event #12: LLM End\n    Breadcrumbs: N/A\n    Duration: N/A\n    Key Outputs: N/A\n\n"
    )

    output = io.StringIO()
    write_report(8, output, event_error)
    assert (
        output.getvalue()
        == "Event #8: Tool Error\n    Error Type: N/A\n    Breadcrumbs: N/A\n    Duration: N/A\n    Error Message: N/A\n\n"
    )

    output = io.StringIO()
    write_report(7, output, logger_warning)
    assert (
        output.getvalue()
        == "Event #7: N/A\n    Handler Class: N/A\n    Method Name: N/A\n    Error Message: N/A\n\n"
    )
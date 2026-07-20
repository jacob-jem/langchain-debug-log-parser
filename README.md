# LANGCHAIN CONSOLE DEBUG PARSER
#### Video Demo: <URL HERE>
#### Description:

## Introduction

This project is a parser that reads LangChain's console debug output, produced by the ConsoleCallbackHandler when `set_debug(True)` is activated, and reformats it into a clean, chronologically ordered, nested report. Rather than making a security analyst scroll through raw JSON and stack traces, the report lists every "event" in the order it happened, indented to reflect its nesting depth, with only the fields that actually matter for reviewing an agent's behavior.

An "event", for this project's purposes, is a log entry representing the start, end, or error of a Runnable (a chain, LLM, tool, or retriever) as recorded in the debug output.

This parser was built and tested against logs generated with LangChain's langchain-ollama integration (ChatOllama), running llama3.2 locally via Ollama. The outer structure of the log (event types, breadcrumbs, timing) comes from LangChain's own tracing system and should work regardless of which model provider generated it. The specific JSON field names inside each event (token usage keys, for instance) have only been verified against Ollama output and may differ for other providers.

## classes.py

Every parsed event becomes an object, not just a dictionary, because different event types genuinely need different attributes, and Python's inheritance made that easy to express cleanly instead of scattering `.get()` calls everywhere.

`Event` is the base class every other event type inherits from. It holds the attributes shared by everything: type, breadcrumbs, and a name derived from the last segment of the breadcrumbs.

`Event_Start` and `Event_End` add a phase attribute and either an input_data or output_data attribute, since a start event has something going in and an end event has something coming out.

LLM events needed more than a generic Event_Start/Event_End could offer, since they carry prompts, token usage, tool calls, and more. `LLM_Start` and `LLM_End` subclass the two above, swapping out the input_data and output_data attributes for a prompts attribute and an llm_fields attribute, respectively. `LLM_End` also holds a start_match attribute, a reference to the specific `LLM_Start` object it corresponds to, which is what lets the final report show which prompt a given response actually answered.

Errors came in two different shapes, so they got two separate classes. `Event_Error` subclasses `Event` directly and represents a Runnable that actually raised an exception during its own execution, complete with breadcrumbs and duration like any other event. `Logger_Warning` is not related to `Event` at all. It represents LangChain's own internal logging code failing while trying to record something, which is a real, known quirk in the version tested. Since it isn't tied to a specific Runnable, it has no breadcrumbs or duration, only a handler, a method, and the exception that occurred.

## project.py

**main** ties everything together: it verifies the input and output files, then reads the log and splits it into a flat list of headers and their following text using a single regex, alternating between event headers and content. It loops through that list two at a time and sorts each piece into an event object before writing it to the report. If sort doesn't recognize a given header, it returns None instead of raising an error, and main writes a plain "Invalid event type" line in its place, so one invalid or unexpected log entry doesn't take down the whole run.

**verify_files** handles the command line interface. It requires `--input` and `--output` flags, both of which must have values that are .txt files, and exits with a clear message otherwise. Missing, extra, or invalid arguments are rejected the same way, and if the input file doesn't exist at all, it also exits immediately. If the output file already exists, it asks the user to confirm before overwriting, accepting "Y" or "N" regardless of case. Declining prompts for a new path instead, and the whole check loops again on that new path.

**sort** takes one header and its following text and returns the matching event object, or None if the header doesn't match any known event type. Breadcrumbs and duration are pulled out with regex. For chain, tool, and retriever events, the content is decoded as JSON when possible and falls back to a direct regex extraction when it isn't, since a fair amount of real content in these logs (like the `[inputs]`/`[outputs]` placeholders LangChain sometimes prints) isn't valid JSON at all. LLM events always decode as JSON, since that's consistently how they're formatted.

The most complex part of sort is matching an LLM_End back to the LLM_Start it belongs to, since the prompt text only ever appears on the start line. This is handled with a dictionary of stacks, keyed by breadcrumbs, where each start gets pushed on and each end pops the most recent one off. This correctly handles sequential and nested calls, including the case where an agent loops back through the same LLM more than once. It does not guarantee a correct match if events are genuinely concurrent or if a start event is missing entirely, which does happen due to a real bug in this version of LangChain where `on_tool_start` sometimes fails to log at all.

**decode** loops through a string character by character looking for the first `{`, then attempts `json.JSONDecoder.raw_decode` from that point, retrying at the next `{` if that one fails. This handles the fact that real log lines mix plain text, error tracebacks, and JSON together in ways a single regex or `json.loads()` call can't cleanly separate.

**get_llm_fields** builds the nested dictionary of prompts, prompt content, candidate responses, and their respective key data fields (content, token usage, tool calls, done reason) that an LLM_End object needs. It returns an empty dictionary if given anything other than a real dictionary, so an incorrectly formatted or missing JSON object doesn't crash the rest of the report.

**write_report** takes an event object and writes it to the output file, indented according to how deeply nested its breadcrumbs are. Since a Logger_Warning object has no breadcrumbs attribute at all, and other event types can have breadcrumbs of None if the regex fails to find any, that indentation calculation checks for both cases before trying to access or count the attribute, so a missing breadcrumbs value falls back to no indentation rather than raising an error. Every field that could plausibly be missing defaults to "N/A" rather than printing the literal word "None", and any text field containing a literal newline (or the literal two characters backslash-n, which shows up depending on whether that particular field came from JSON decoding or regex extraction) gets converted to " → " so multi-line content stays on one line without breaking the report's formatting.

## test_project.py

Each function above has its own test. 

**test_verify_files** patches sys.argv, os.path.exists, and input to check every path through the argument validation and overwrite confirmation logic, including invalid or missing flags and values, and the retry loop for a bad replacement filename. 

**test_sort** feeds real (verified) LangChain log segments through the function for every event type and checks the resulting object's attributes. It also covers three edge cases: an empty header with empty text, which confirms None values are handled safely rather than causing a crash; a header that matches no known event type, which confirms sort returns None instead of raising an error; and a header that starts with "Error in" but doesn't match the full logger warning pattern, confirming a Logger_Warning is still created with all attributes set to None rather than crashing.

**test_decode** checks both text containing a real JSON object and plain text that isn't JSON. 

**test_get_llm_fields** checks a properly formed input and confirms non-dictionary input returns an empty dictionary instead of raising an error. 

**test_write_report** uses `io.StringIO` as a stand-in file object, so the exact text written to the report can be checked directly without creating real files on disk. It confirms both the normal output for every event type and the fallback output, with "N/A" in place of missing data, when an event is constructed with entirely None attributes.

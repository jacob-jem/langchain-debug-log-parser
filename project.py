"""
Parses LangChain's console debug output into a clean, chronologically ordered,
nested report. Reads a log file, splits it into individual events, sorts each
into the appropriate event object, and writes a clear summary of each one to
an output file.
"""

import argparse
import sys
import os
import re
import json
from classes import (
    Event_Start,
    Event_End,
    LLM_Start,
    LLM_End,
    Event_Error,
    Logger_Warning,
)


def main():
    """Verify the input/output files, parse the log, and write the report."""

    files = verify_files()

    starts_stack = {}

    with open(files.input) as log, open(files.output, "w") as report:
        contents = log.read()

        events = re.split(
            r"(\[(?:chain|llm|tool|retriever)/(?:start|end|error)\]|(?:Error in.+))",
            contents,
        )

        for i in range(1, len(events), 2):
            n = (i + 1) // 2 if i != 1 else 1
            header, text = events[i].strip("[]"), events[i + 1].strip()
            event = sort(header, text, starts_stack)
            if event:
                write_report(n, report, event)
            else:
                report.write(
                    f"Event #{n}: Invalid event type: {header}\n\n"
                )


def verify_files():
    """Validate command line arguments and confirm before overwriting an existing output file."""

    argparser = argparse.ArgumentParser(
        description="Parse a LangChain log file and generate a report of events."
    )
    argparser.add_argument(
        "--input", help="Path to the log file to parse", required=True
    )
    argparser.add_argument(
        "--output", help="Path to the report file to generate", required=True
    )

    args = argparser.parse_args()

    while True:

        if not (args.input.endswith(".txt") and args.output.endswith(".txt")):
            sys.exit("Error: Input LangChain log and output report must be .txt files.")

        if not os.path.exists(args.input):
            sys.exit(f"Error: File '{args.input}' not found.")

        if os.path.exists(args.output):

            response = input(
                "The output report file already exists. Are you sure you want to overwrite it? Y/N "
            )

            if response.upper() == "Y":
                break

            elif response.upper() == "N":
                args.output = input("Please enter your new output report file path: ")

            else:
                print("Invalid response.")

        else:
            break

    return args


def sort(header, text, starts_stack):
    """Take one event header and its following text, and return the matching event object."""

    breadcrumbs = (
        match.group(1).strip() if (match := re.search(r"\[(.+?)\]", text)) else None
    )

    duration = (
        match.group(1).strip()
        if (match := re.search(r"\[(\d+((?:\.\d{1,2})?m?s))\]", text))
        else None
    )

    if not (header.endswith("/error") or header.startswith("Error in")):
        data = decode(text) if text else None

    if header.endswith("/start") and header != "llm/start":
        type = header.split("/")[0]
        if data:
            input_data = data
        else:
            input_data = (
                match.group(1).strip()
                if (
                    match := re.search(
                        rf"Entering {type.title()} run with input:\n(.+)",
                        text,
                        re.DOTALL,
                    )
                )
                else None
            )
        return Event_Start(type, breadcrumbs, input_data)

    elif header.endswith("/end") and header != "llm/end":
        type = header.split("/")[0]
        if data:
            output_data = data
        else:
            output_data = (
                match.group(1).strip()
                if (
                    match := re.search(
                        rf"Exiting {type.title()} run with output:\n(.+)",
                        text,
                        re.DOTALL,
                    )
                )
                else None
            )
        return Event_End(type, breadcrumbs, duration, output_data)

    elif header == "llm/start":
        type = "llm"
        prompts = data.get("prompts", []) if data else []
        llm_start = LLM_Start(type, breadcrumbs, prompts)
        starts_stack.setdefault(llm_start.breadcrumbs, []).append(llm_start)
        return llm_start

    elif header == "llm/end":

        type = "llm"

        start_match = (
            starts_stack[breadcrumbs].pop() if starts_stack.get(breadcrumbs) else None
        )

        llm_fields = get_llm_fields(data, start_match)

        return LLM_End(
            type,
            breadcrumbs,
            duration,
            llm_fields,
            start_match,
        )

    elif header.endswith("/error"):
        type = header.split("/")[0]

        name, message = (
            (match.group(1).strip('"'), match.group(2).strip("'"))
            if (match := re.search(r"run errored with error:\n(.+?)\((.+?)\)", text))
            else (None, None)
        )

        return Event_Error(name, type, breadcrumbs, duration, message)

    elif header.startswith("Error in"):
        name, handler, method, message = (
            (
                match.group(3).strip(),
                match.group(1).strip(),
                match.group(2).strip(),
                match.group(4).strip("'"),
            )
            if (
                match := re.search(
                    r"Error in (.+?)\.(.+?) callback: (.+)\((.+?)\)", header
                )
            )
            else (None, None, None, None)
        )

        return Logger_Warning(name, handler, method, message)


def decode(text):
    """Find and parse the JSON object in a string, returning None if there isn't one."""

    decoder = json.JSONDecoder()

    for i, letter in enumerate(text):
        if letter == "{":
            try:
                data, _ = decoder.raw_decode(text, idx=i)
                return data
            except json.JSONDecodeError:
                continue


def get_llm_fields(data, start_match):
    """Build the nested dictionary of prompts, candidate responses, and their key output fields for an LLM_End object."""

    llm_fields = {}

    if isinstance(data, dict):
        for i, prompt in enumerate(data.get("generations", [])):

            input_prompt = (
                start_match.prompts[i]
                if start_match and i < len(start_match.prompts)
                else None
            )

            llm_fields[f"Prompt {i + 1}"] = {
                "Prompt Content": input_prompt,
                "Candidate Responses": {},
            }

            for n, candidate_response in enumerate(prompt):

                kwargs = candidate_response.get("message", {}).get("kwargs", {})

                content_data = kwargs.get("content")
                token_data = kwargs.get("usage_metadata")
                tool_data = kwargs.get("tool_calls")
                done_data = kwargs.get("response_metadata", {}).get("done_reason")

                llm_fields[f"Prompt {i + 1}"]["Candidate Responses"][
                    f"Candidate Response {n + 1}"
                ] = {
                    "content": content_data,
                    "token_usage": token_data,
                    "tool_calls": tool_data,
                    "done_reason": done_data,
                }

    return llm_fields


def write_report(n, report, event):
    """Write an event's details to the report file, indented according to its nesting depth."""

    indent = "    "
    nested_indent = (
        indent * event.breadcrumbs.count(" > ")
        if not isinstance(event, Logger_Warning) and event.breadcrumbs
        else ""
    )

    if not isinstance(event, Event_Error) and not isinstance(event, Logger_Warning):
        
        if event.type == "llm":
            report.write(
            f"{nested_indent}Event #{n}: {(event.type).upper()} {(event.phase).title()}\n"
            )
        else:
            report.write(
                f"{nested_indent}Event #{n}: {(event.type).title()} {(event.phase).title()}\n"
            )
        report.write(
            f"{nested_indent}{indent}Breadcrumbs: {event.breadcrumbs if event.breadcrumbs else "N/A"}\n"
        )

    if isinstance(event, Event_Start) and not isinstance(event, LLM_Start):
        report.write(
            f"{nested_indent}{indent}Input: {str(event.input_data).replace("\\n", " → ").replace("\n", " → ") if event.input_data else "N/A"}\n"
        )

    elif isinstance(event, Event_End) and not isinstance(event, LLM_End):
        report.write(
            f"{nested_indent}{indent}Duration: {event.duration if event.duration else "N/A"}\n"
        )
        report.write(
            f"{nested_indent}{indent}Output: {str(event.output_data).replace("\\n", " → ").replace("\n", " → ") if event.output_data else "N/A"}\n"
        )

    elif isinstance(event, LLM_Start):
        if event.prompts:
            report.write(f"{nested_indent}{indent}LLM Prompts:\n")
            for i, prompt in enumerate(event.prompts):
                report.write(
                    f"{nested_indent}{indent * 2} Prompt {i + 1}: {prompt.replace("\\n", " → ").replace("\n", " → ") if prompt else None}\n"
                )
        else:
            report.write(f"{nested_indent}{indent}LLM Prompts: N/A\n")

    elif isinstance(event, LLM_End):
        report.write(
            f"{nested_indent}{indent}Duration: {event.duration if event.duration else "N/A"}\n"
        )

        if event.llm_fields != {}:

            report.write(f"{nested_indent}{indent}Key Outputs:\n")
            for prompt, prompt_values in event.llm_fields.items():
                report.write(
                    f"{nested_indent}{indent * 2}{prompt}: {prompt_values['Prompt Content'].replace("\\n", " → ").replace('\n', ' → ') if prompt_values['Prompt Content'] else "N/A"}\n"
                )
                for response, response_values in prompt_values[
                    "Candidate Responses"
                ].items():
                    report.write(f"{nested_indent}{indent * 3}{response}:\n")
                    for key, value in response_values.items():
                        if key == "content" and value is not None:
                            report.write(
                                f"{nested_indent}{indent * 4}{key}: {value.replace("\\n", " → ").replace('\n', ' → ')}\n"
                            )
                        else:
                            report.write(
                                f"{nested_indent}{indent * 4}{key}: {value if value else "N/A"}\n"
                            )
        else:
            report.write(f"{nested_indent}{indent}Key Outputs: N/A\n")

    elif isinstance(event, Event_Error):
        report.write(
            f"{nested_indent}Event #{n}: {(event.type).title()} {(event.phase).title()}\n"
        )
        report.write(
            f"{nested_indent}{indent}Error Type: {event.name if event.name else "N/A"}\n"
        )
        report.write(
            f"{nested_indent}{indent}Breadcrumbs: {event.breadcrumbs if event.breadcrumbs else "N/A"}\n"
        )
        report.write(
            f"{nested_indent}{indent}Duration: {event.duration if event.duration else "N/A"}\n"
        )
        report.write(
            f"{nested_indent}{indent}Error Message: {event.message if event.message else "N/A"}\n"
        )

    elif isinstance(event, Logger_Warning):
        report.write(
            f"{nested_indent}Event #{n}: {(event.name) if event.name else "N/A"}\n"
        )
        report.write(
            f"{nested_indent}{indent}Handler Class: {event.handler if event.handler else "N/A"}\n"
        )
        report.write(
            f"{nested_indent}{indent}Method Name: {event.method if event.method else "N/A"}\n"
        )
        report.write(
            f"{nested_indent}{indent}Error Message: {event.message if event.message else "N/A"}\n"
        )

    report.write("\n")


if __name__ == "__main__":
    main()

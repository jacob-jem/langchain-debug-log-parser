class Event:
    def __init__(self, type, breadcrumbs):
        self.type = type
        self.breadcrumbs = breadcrumbs
        self.name = ((breadcrumbs.split(" > ")[-1]).split(":")[-1]).title() if breadcrumbs else None


class Event_Start(Event):
    def __init__(self, type, breadcrumbs, input_data):
        super().__init__(type, breadcrumbs)
        self.phase = "start"
        self.input_data = input_data


class Event_End(Event):
    def __init__(self, type, breadcrumbs, duration, output_data):
        super().__init__(type, breadcrumbs)
        self.phase = "end"
        self.duration = duration
        self.output_data = output_data


class LLM_Start(Event_Start):
    def __init__(self, type, breadcrumbs, prompts):
        super().__init__(type, breadcrumbs, None)
        self.prompts = prompts
        del self.input_data


class LLM_End(Event_End):
    def __init__(
        self,
        type,
        breadcrumbs,
        duration,
        llm_fields,
        start_match,
    ):
        super().__init__(type, breadcrumbs, duration, None)
        self.llm_fields = llm_fields
        self.start_match = start_match
        del self.output_data


class Event_Error(Event):
    def __init__(self, name, type, breadcrumbs, duration, message):
        super().__init__(type, breadcrumbs)
        self.name = name
        self.phase = "error"
        self.duration = duration
        self.message = message


class Logger_Warning:
    def __init__(self, name, handler, method, message):
        self.name = name
        self.handler = handler
        self.method = method
        self.message = message

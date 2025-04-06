from abc import ABC, abstractmethod

class BaseAgent(ABC):
    @abstractmethod
    def build_prompt(self, *args, **kwargs):
        """Build the prompt for the agent."""
        pass

import { useState } from "react";
import { Button } from "@headlessui/react";
import { Input } from "@headlessui/react";

export default function AutomationFrameworkUI() {
  const [command, setCommand] = useState("");
  const [logs, setLogs] = useState<string[]>([]);

  const handleExecute = () => {
    if (!command.trim()) return;
    setLogs([command, ...logs]);
    setCommand(""); // Clear input after execution
  };

  return (
    <div className="flex h-screen items-center justify-center bg-gray-100 p-6">
      <div className="w-full max-w-lg bg-white shadow-lg rounded-lg p-6">
        <h2 className="text-2xl font-bold mb-4">Automation Framework</h2>

        {/* Input Field using Headless UI */}
        <Input
          type="text"
          className="w-full p-2 border border-gray-300 rounded-md focus:ring focus:ring-gray-500"
          placeholder="Describe what you want (e.g., 'Create a GitHub Actions Pipeline')"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
        />

        {/* Execute Button using Headless UI */}
        <Button
          className="w-full bg-black text-white px-4 py-2 rounded mt-4 hover:bg-gray-800 focus:ring focus:ring-gray-500 disabled:bg-gray-400"
          onClick={handleExecute}
          disabled={!command.trim()}
        >
          Execute
        </Button>
      </div>
    </div>
  );
}

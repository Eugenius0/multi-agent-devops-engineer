import { useState } from "react";
import { Button, Input } from "@headlessui/react";
import { useMutation } from "@tanstack/react-query";

export default function AutomationFrameworkUI() {
  const [command, setCommand] = useState("");
  const [logs, setLogs] = useState<
    { taskId: string; status: string; executedTask: string; output: string }[]
  >([]);

  // Send command to FastAPI backend
  const mutation = useMutation({
    mutationFn: async (cmd: string) => {
      const response = await fetch("http://localhost:8000/run-automation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_input: cmd }),
      });

      if (!response.ok) throw new Error("Failed to execute automation");
      return response.json();
    },
    onSuccess: (data) => {
      setLogs((prevLogs) => [
        {
          taskId: data.task_id,
          status: data.status,
          executedTask: data.executed_task,
          output: data.output,
        },
        ...prevLogs,
      ]);
      setCommand(""); // Clear input after execution
    },
    onError: (error) => {
      setLogs((prevLogs) => [
        {
          taskId: "N/A",
          status: "Error",
          executedTask: "N/A",
          output: error.message,
        },
        ...prevLogs,
      ]);
    },
  });

  return (
    <div className="flex h-screen items-center justify-center bg-gray-300 p-6">
      <div className="w-full max-w-lg bg-white shadow-lg rounded-lg p-6">
        <h2 className="text-2xl font-bold mb-4">Automation Framework</h2>

        {/* Input Field using Headless UI */}
        <Input
          type="text"
          className="w-full p-2 border border-gray-300 rounded-md focus:ring focus:ring-gray-500"
          placeholder="Describe what you want (e.g., 'Create a GitHub Actions pipeline')"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
        />

        {/* Execute Button using Headless UI */}
        <Button
          className="w-full bg-black text-white px-4 py-2 rounded mt-4 hover:bg-gray-800 focus:ring focus:ring-gray-500 disabled:bg-gray-400"
          onClick={() => mutation.mutate(command)}
          disabled={!command.trim() || mutation.isPending}
        >
          {mutation.isPending ? "Processing..." : "Execute"}
        </Button>

        {/* Execution Logs */}
        <div className="mt-6">
          <h3 className="text-lg font-semibold mb-2">Execution History</h3>
          {logs.length === 0 ? (
            <p className="text-gray-500">No executions yet.</p>
          ) : (
            <div className="space-y-2">
              {logs.map((log) => (
                <div
                  key={log.taskId}
                  className="p-3 bg-gray-100 border border-gray-300 rounded-lg shadow-sm"
                >
                  <p className="font-semibold">{log.executedTask}</p>
                  <p className="text-sm text-gray-600">{log.status}</p>
                  <pre className="text-xs text-gray-500">{log.output}</pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

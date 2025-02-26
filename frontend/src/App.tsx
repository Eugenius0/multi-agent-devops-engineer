import { useState } from "react";
import { Button, Input } from "@headlessui/react";
import { useMutation } from "@tanstack/react-query";

export default function AutomationFrameworkUI() {
  const [command, setCommand] = useState("");
  const [repoName, setRepoName] = useState("");
  const [logs, setLogs] = useState<
    { taskId: string; status: string; output: string }[]
  >([]);

  // Send command and repoName to FastAPI backend and stream logs
  const mutation = useMutation({
    mutationFn: async ({ cmd, repo }: { cmd: string; repo: string }) => {
      const response = await fetch("http://localhost:8000/run-automation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_input: cmd, repo_name: repo }),
      });

      if (!response.ok) throw new Error("Failed to execute automation");

      const taskId = crypto.randomUUID(); // Generate a task ID for tracking
      setLogs((prevLogs) => [
        { taskId, status: "Running", output: "" },
        ...prevLogs,
      ]);

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response stream available");

      const decoder = new TextDecoder();
      let newOutput = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        newOutput += decoder.decode(value, { stream: true });

        // eslint-disable-next-line no-loop-func
        setLogs((prevLogs) =>
          prevLogs.map((log) =>
            log.taskId === taskId
              ? { ...log, output: newOutput, status: "Running" }
              : log
          )
        );
      }

      setLogs((prevLogs) =>
        prevLogs.map((log) =>
          log.taskId === taskId ? { ...log, status: "Completed" } : log
        )
      );
    },
    onError: (error) => {
      setLogs((prevLogs) => [
        { taskId: "N/A", status: "Error", output: error.message },
        ...prevLogs,
      ]);
    },
  });

  return (
    <div className="flex h-screen items-center justify-center bg-gray-300 p-6">
      <div className="w-full max-w-lg bg-white shadow-lg rounded-lg p-6">
        <h2 className="text-2xl font-bold mb-4">Automation Framework</h2>

        {/* Input Fields */}
        <Input
          type="text"
          className="w-full p-2 border border-gray-300 rounded-md focus:ring focus:ring-gray-500"
          placeholder="Describe what you want (e.g., 'Create a GitHub Actions pipeline')"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
        />
        <Input
          type="text"
          className="w-full p-2 border border-gray-300 rounded-md focus:ring focus:ring-gray-500 mt-2"
          placeholder="Enter your GitHub repository name"
          value={repoName}
          onChange={(e) => setRepoName(e.target.value)}
        />

        {/* Execute Button */}
        <Button
          className="w-full bg-black text-white px-4 py-2 rounded mt-4 hover:bg-gray-800 focus:ring focus:ring-gray-500 disabled:bg-gray-400"
          onClick={() => mutation.mutate({ cmd: command, repo: repoName })}
          disabled={!command.trim() || !repoName.trim() || mutation.isPending}
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
                  <p className="font-semibold">{log.status}</p>
                  <pre className="text-xs text-gray-500 whitespace-pre-wrap">
                    {log.output}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

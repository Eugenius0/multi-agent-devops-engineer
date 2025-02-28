import { useEffect, useRef, useState } from "react";
import { Button, Input } from "@headlessui/react";
import { useMutation } from "@tanstack/react-query";

export default function AutomationFrameworkUI() {
  const [command, setCommand] = useState("");
  const [repoName, setRepoName] = useState("");
  const [executionStatus, setExecutionStatus] = useState(""); // Keep execution status visible
  const [logs, setLogs] = useState<
    {
      taskId: string;
      status: string;
      executedTask: string;
      timestamp: string;
    }[]
  >([]);

  const logsEndRef = useRef<HTMLDivElement>(null); // 🔹 Ref for scrolling

  // Auto-scroll when executionStatus updates
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [executionStatus]);

  // Function to determine executed task name
  const getExecutedTaskName = (rawOutput: string) => {
    if (rawOutput.includes("GitHub")) {
      return "✅ Creation of GitHub Actions pipeline";
    } else if (rawOutput.includes("Docker")) {
      return "✅ Containerization of your app with Docker";
    }
    return "✅ Executed your indicated automation task"; // Fallback if unknown
  };

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
      setExecutionStatus(""); // Clear previous status

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response stream available");

      const decoder = new TextDecoder();
      let newOutput = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        newOutput += decoder.decode(value, { stream: true });

        setExecutionStatus(newOutput); // Keep live execution logs visible
      }

      // Extract readable task name
      const executedTask = getExecutedTaskName(newOutput);

      // Store completed execution in history
      setLogs((prevLogs) => [
        {
          taskId,
          status: `Completed ${executedTask}`,
          executedTask,
          timestamp: new Date().toLocaleString(), // Save timestamp
        },
        ...prevLogs,
      ]);
    },
    onError: (error) => {
      setExecutionStatus("Error occurred during execution.");
      setLogs((prevLogs) => [
        {
          taskId: "N/A",
          status: "Error",
          executedTask: "N/A",
          timestamp: new Date().toLocaleString(),
        },
        ...prevLogs,
      ]);
    },
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-300 p-6">
      <div className="w-full max-w-lg h-full bg-white shadow-lg rounded-lg p-6 overflow-y-auto">
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

        {/* Execution Status (Live & Persistent) */}
        {executionStatus && (
          <div className="mt-6 p-3 bg-blue-100 border border-blue-300 rounded-lg shadow-sm max-h-60 overflow-y-auto ">
            <h3 className="text-lg font-semibold">Execution Status</h3>
            <pre className="text-xs text-gray-700 whitespace-pre-wrap">
              {executionStatus}
            </pre>
            <div ref={logsEndRef} /> {/* ensures auto-scrolling */}
          </div>
        )}

        {/* Execution History */}
        <div className="mt-6 max-h-60 overflow-y-auto">
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
                  <p className="text-sm text-gray-600">{log.timestamp}</p>
                  <p className="font-semibold">{log.status}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

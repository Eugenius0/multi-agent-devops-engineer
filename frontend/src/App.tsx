import { useEffect, useRef, useState } from "react";
import { Button, Input } from "@headlessui/react";
import { useMutation } from "@tanstack/react-query";

export default function AutomationFrameworkUI() {
  const [command, setCommand] = useState("");
  const [repoName, setRepoName] = useState("");
  const [executionStatus, setExecutionStatus] = useState("");
  const [logs, setLogs] = useState<
    {
      taskId: string;
      status: string;
      executedTask: string;
      timestamp: string;
      executionTime: string;
    }[]
  >([]);

  const logsEndRef = useRef<HTMLDivElement>(null);
  const controllerRef = useRef<AbortController | null>(null);

  const [startTime, setStartTime] = useState<number | null>(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [finalExecutionTime, setFinalExecutionTime] = useState<string | null>(
    null
  );
  const [isCancelling, setIsCancelling] = useState(false);

  // Auto-scroll when executionStatus updates
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [executionStatus]);

  // Timer Effect
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;

    if (isRunning && startTime !== null) {
      interval = setInterval(() => {
        setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
      }, 1000);
    }

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [isRunning, startTime]);

  const getExecutedTaskName = (rawOutput: string) => {
    if (rawOutput.includes("AWS")) return "✅ Deployment of your app to Cloud";
    if (rawOutput.includes("GitHub"))
      return "✅ Creation of GitHub Actions pipeline";
    if (rawOutput.includes("Docker"))
      return "✅ Containerization of your app with Docker";
    if (rawOutput.includes("GitLab"))
      return "✅ Creation of GitLab CI/CD pipeline";
    if (rawOutput.includes("Kubernetes"))
      return "✅ Deployment of your app to Kubernetes";
    return "✅ Executed your indicated automation task";
  };

  // Start Automation Mutation
  const mutation = useMutation({
    mutationFn: async ({ cmd, repo }: { cmd: string; repo: string }) => {
      setExecutionStatus("");
      setElapsedTime(0);
      setStartTime(Date.now());
      setIsRunning(true);
      setFinalExecutionTime(null);

      controllerRef.current = new AbortController();

      const response = await fetch("http://localhost:8000/run-automation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_input: cmd, repo_name: repo }),
        signal: controllerRef.current.signal, // Attach abort signal
      });

      if (!response.ok) throw new Error("Failed to execute automation");

      const taskId = crypto.randomUUID();
      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response stream available");

      const decoder = new TextDecoder();
      let newOutput = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        newOutput += decoder.decode(value, { stream: true });
        setExecutionStatus(newOutput);
      }

      setIsRunning(false);
      setFinalExecutionTime(`${elapsedTime} seconds`);

      const executedTask = getExecutedTaskName(newOutput);
      setLogs((prevLogs) => [
        {
          taskId,
          status: `Completed ${executedTask}`,
          executedTask,
          timestamp: new Date().toLocaleString(),
          executionTime: `${elapsedTime} seconds`,
        },
        ...prevLogs,
      ]);
    },
    onError: (error) => {
      if (error.name === "AbortError") {
        setExecutionStatus("❌ Execution Cancelled.");
      } else {
        setExecutionStatus("❌ Error occurred during execution.");
      }
      setIsRunning(false);
    },
  });

  const handleCancel = async () => {
    if (isCancelling) return; // Prevent multiple cancel requests

    setIsCancelling(true); // Indicate cancellation is in progress

    try {
      if (controllerRef.current) {
        controllerRef.current.abort(); // Abort frontend fetch
      }
      await fetch("http://localhost:8000/cancel-automation", {
        method: "POST",
      });

      setExecutionStatus("❌ Execution Cancelled.");
    } catch (error) {
      console.warn("Cancel request failed:", error);
    } finally {
      setIsRunning(false);
      setIsCancelling(false); // Allow execution again after cancel is fully processed
    }
  };

  let cancelButtonColor = "bg-red-300 cursor-not-allowed"; // Default

  if (isCancelling) {
    cancelButtonColor = "bg-yellow-500 cursor-wait";
  } else if (isRunning) {
    cancelButtonColor = "bg-red-600 hover:bg-red-700";
  }

  const cancelButtonText = isCancelling ? "Cancelling..." : "Cancel";

  let executionTimerDisplay = null;

  if (finalExecutionTime) {
    executionTimerDisplay = (
      <div className="mt-4 text-center text-gray-600 text-sm">
        ⏳ Total Execution Time: {finalExecutionTime}
      </div>
    );
  } else if (isRunning) {
    executionTimerDisplay = (
      <div className="mt-4 text-center text-gray-600 text-sm">
        ⏳ Execution Time: {elapsedTime} seconds
      </div>
    );
  }

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
          className={`w-full text-white px-4 py-2 rounded mt-4 flex justify-center items-center ${
            !command.trim() ||
            !repoName.trim() ||
            mutation.isPending ||
            isCancelling
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-black hover:bg-gray-800 focus:ring focus:ring-gray-500"
          }`}
          onClick={() => mutation.mutate({ cmd: command, repo: repoName })}
          disabled={
            !command.trim() ||
            !repoName.trim() ||
            mutation.isPending ||
            isCancelling // ✅ Ensure execute button is disabled while cancelling
          }
        >
          {mutation.isPending || isCancelling ? "Processing..." : "Execute"}
        </Button>

        {/* Cancel Button */}
        <Button
          className={`w-full text-white px-4 py-2 rounded mt-2 ${cancelButtonColor}`}
          onClick={handleCancel}
          disabled={!isRunning || isCancelling} // Prevent multiple cancels
        >
          {cancelButtonText}
        </Button>

        {/* Execution Timer Display */}
        {executionTimerDisplay}

        {/* Execution Status */}
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
                  <p className="text-xs text-gray-500">
                    ⏳ {log.executionTime}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

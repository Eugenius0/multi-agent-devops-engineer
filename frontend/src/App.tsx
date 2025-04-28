import { useEffect, useRef, useState } from "react";
import { Button, Input } from "@headlessui/react";
import { useMutation } from "@tanstack/react-query";
import { Maximize } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { Loader2 } from "lucide-react";

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
  const [pendingApproval, setPendingApproval] = useState<{
    taskId: string;
    action: string;
  } | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedAction, setEditedAction] = useState<string>("");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isFadingOutApproval, setIsFadingOutApproval] = useState(false);

  useEffect(() => {
    setIsEditing(false);
  }, [pendingApproval]);

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

  const getExecutedTaskName = (_rawOutput: string) => {
    return "🤖 AI DevOps Agent completed the requested automation";
  };

  const parseApprovalTag = (line: string) => {
    const approvalRegex = /\[ApprovalRequired\]\s(.+?)\s→\s(.+)/;
    const match = approvalRegex.exec(line);
    if (match) {
      return { taskId: match[1], action: match[2] };
    }
    return null;
  };

  const sendApproval = async (approved: boolean) => {
    if (!pendingApproval) return;
    const { taskId } = pendingApproval;
    try {
      await fetch("http://localhost:8000/approve-action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_id: taskId,
          approved,
          edited_command: editedAction,
        }),
      });
      setPendingApproval(null);
    } catch (err) {
      console.error("Failed to send approval:", err);
    }
  };

  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isFullscreen && modalRef.current) {
      modalRef.current.focus(); // Set focus when fullscreen opens
    }
  }, [isFullscreen]);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsFullscreen(false);
    };
    if (isFullscreen) {
      window.addEventListener("keydown", handleEscape);
    }
    return () => {
      window.removeEventListener("keydown", handleEscape);
    };
  }, [isFullscreen]);

  const mutation = useMutation({
    mutationFn: async ({ cmd, repo }: { cmd: string; repo: string }) => {
      setExecutionStatus("");
      setIsFadingOutApproval(true);
      setTimeout(() => {
        setPendingApproval(null);
        setIsFadingOutApproval(false);
      }, 300); // match this duration with your fade transition (300ms)
      setElapsedTime(0);
      setStartTime(Date.now());
      setIsRunning(true);
      setFinalExecutionTime(null);

      controllerRef.current = new AbortController();

      const response = await fetch("http://localhost:8000/run-automation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_input: cmd, repo_name: repo }),
        signal: controllerRef.current.signal,
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

        const chunk = decoder.decode(value, { stream: true });
        newOutput += chunk;
        setExecutionStatus(newOutput);

        const approval = parseApprovalTag(chunk);
        if (approval) {
          setPendingApproval(approval);
          if (!isEditing) {
            setEditedAction(approval.action);
          }
        }
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
    if (isCancelling) return;

    setIsCancelling(true);
    setPendingApproval(null);

    try {
      if (controllerRef.current) {
        controllerRef.current.abort();
      }
      await fetch("http://localhost:8000/cancel-automation", {
        method: "POST",
      });

      setExecutionStatus("❌ Execution Cancelled.");
    } catch (error) {
      console.warn("Cancel request failed:", error);
    } finally {
      setIsRunning(false);
      setIsCancelling(false);
    }
  };

  let cancelButtonColor = "bg-red-300 cursor-not-allowed";

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
        <h2 className="text-2xl font-bold mb-4">
          Eugenius Multi Agent Devops Engineer
        </h2>

        <textarea
          className="w-full p-3 border border-gray-300 rounded-md focus:ring focus:ring-gray-500 text-sm resize-y min-h-[100px]"
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
            isCancelling
          }
        >
          {mutation.isPending || isCancelling ? (
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Processing...
            </div>
          ) : (
            "Execute"
          )}
        </Button>

        <Button
          className={`w-full text-white px-4 py-2 rounded mt-2 ${cancelButtonColor}`}
          onClick={handleCancel}
          disabled={!isRunning || isCancelling}
        >
          {cancelButtonText}
        </Button>

        {executionTimerDisplay}

        <AnimatePresence>
          {executionStatus && (
            <motion.div
              key="executionStatus"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.4 }}
              className="mt-6 p-3 bg-blue-100 border border-blue-300 rounded-lg shadow-sm max-h-60 overflow-y-auto"
            >
              <h3 className="text-lg font-semibold">Execution Status</h3>
              <pre className="text-xs text-gray-700 whitespace-pre-wrap">
                {executionStatus}
              </pre>
              <div ref={logsEndRef} />
              <div className="mt-2 flex justify-end">
                <button
                  className="text-blue-700 hover:text-blue-900"
                  onClick={() => setIsFullscreen(true)}
                >
                  <Maximize className="w-5 h-5" />
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {pendingApproval && !isFadingOutApproval && (
            <motion.div
              key="approval-box"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
              className="mt-4 p-4 border border-yellow-400 bg-yellow-100 rounded-md shadow-sm"
            >
              <p className="text-sm font-medium mb-2">
                🛑 Awaiting approval for:
              </p>

              {isEditing ? (
                <textarea
                  className="w-full text-xs border border-gray-300 p-2 rounded mb-3"
                  rows={4}
                  value={editedAction}
                  onChange={(e) => setEditedAction(e.target.value)}
                ></textarea>
              ) : (
                <code className="text-xs block mb-3 text-gray-700 whitespace-pre-wrap">
                  {editedAction}
                </code>
              )}

              <div className="flex gap-2">
                {isEditing ? (
                  <>
                    <Button
                      className="bg-green-700 hover:bg-green-800 text-white px-4 py-2 rounded"
                      onClick={() => setIsEditing(false)}
                    >
                      💾 Save Edit
                    </Button>
                    <Button
                      className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded"
                      onClick={() => {
                        if (pendingApproval) {
                          setEditedAction(pendingApproval.action); // reset to original
                        }
                        setIsEditing(false);
                      }}
                    >
                      ↩️ Cancel Edit
                    </Button>
                  </>
                ) : (
                  <>
                    <Button
                      className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded"
                      onClick={() => sendApproval(true)}
                    >
                      ✅ Approve
                    </Button>
                    <Button
                      className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded"
                      onClick={() => sendApproval(false)}
                    >
                      ❌ Reject
                    </Button>
                    <Button
                      className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded"
                      onClick={() => setIsEditing(true)}
                    >
                      ✏️ Edit
                    </Button>
                  </>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {isFullscreen && (
          <div
            className="fixed inset-0 bg-black bg-opacity-70 z-50 flex items-center justify-center"
            onClick={() => setIsFullscreen(false)}
            aria-hidden="true"
          >
            <div
              className="bg-blue-100 w-11/12 h-5/6 rounded-lg shadow-lg overflow-hidden relative flex flex-col"
              onClick={(e) => e.stopPropagation()}
              aria-hidden="true"
              tabIndex={-1}
              onKeyDown={(e) => {
                if (e.key === "Escape") setIsFullscreen(false); // optional
              }}
            >
              {/* Sticky Header */}
              <div className="sticky top-0 z-10 bg-white border-b border-gray-300 px-4 py-3 flex items-center justify-between">
                {/* Title on the left */}
                <h3 className="text-xl font-bold flex-1 text-left">
                  📋 Fullscreen Execution Status
                </h3>

                {/* Execute & Cancel buttons in the center */}
                <div className="flex gap-3 items-center justify-center flex-1">
                  <Button
                    className={`text-white text-base font-medium px-5 py-2 rounded ${
                      !command.trim() ||
                      !repoName.trim() ||
                      mutation.isPending ||
                      isCancelling
                        ? "bg-gray-400 cursor-not-allowed"
                        : "bg-black hover:bg-gray-800 focus:ring focus:ring-gray-500"
                    }`}
                    onClick={() =>
                      mutation.mutate({ cmd: command, repo: repoName })
                    }
                    disabled={
                      !command.trim() ||
                      !repoName.trim() ||
                      mutation.isPending ||
                      isCancelling
                    }
                  >
                    {mutation.isPending || isCancelling ? (
                      <div className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Processing...
                      </div>
                    ) : (
                      "Execute"
                    )}
                  </Button>

                  <Button
                    className={`text-white text-base font-medium px-5 py-2 rounded ${
                      isCancelling
                        ? "bg-yellow-500 cursor-wait"
                        : isRunning
                        ? "bg-red-600 hover:bg-red-700"
                        : "bg-red-300 cursor-not-allowed"
                    }`}
                    onClick={handleCancel}
                    disabled={!isRunning || isCancelling}
                  >
                    {isCancelling ? "Cancelling..." : "Cancel"}
                  </Button>
                </div>

                {/* Close button on the right */}
                <div className="flex-1 flex justify-end">
                  <button
                    className="bg-gray-800 text-white px-3 py-1 rounded hover:bg-gray-700"
                    onClick={() => setIsFullscreen(false)}
                  >
                    Close
                  </button>
                </div>
              </div>

              {/* Scrollable Body */}
              <div className="flex-1 overflow-y-auto p-6">
                {(finalExecutionTime || isRunning) && (
                  <div className="mb-4 text-center text-gray-700 text-base font-medium">
                    {finalExecutionTime
                      ? `⏳ Total Execution Time: ${finalExecutionTime}`
                      : `⏳ Execution Time: ${elapsedTime} seconds`}
                  </div>
                )}

                <pre className="text-sm text-gray-800 whitespace-pre-wrap mb-6">
                  {executionStatus}
                  <div ref={logsEndRef} />
                </pre>

                {/* Pending Approval */}
                {pendingApproval && (
                  <div className="mt-4 p-4 border border-yellow-400 bg-yellow-100 rounded-md shadow-sm">
                    <p className="text-sm font-medium mb-2">
                      🛑 Awaiting approval for:
                    </p>
                    {isEditing ? (
                      <textarea
                        className="w-full text-xs border border-gray-300 p-2 rounded mb-3"
                        rows={4}
                        value={editedAction}
                        onChange={(e) => setEditedAction(e.target.value)}
                      ></textarea>
                    ) : (
                      <code className="text-xs block mb-3 text-gray-700 whitespace-pre-wrap">
                        {editedAction}
                      </code>
                    )}

                    <div className="flex gap-2">
                      {isEditing ? (
                        <>
                          <Button
                            className="bg-green-700 hover:bg-green-800 text-white px-4 py-2 rounded"
                            onClick={() => setIsEditing(false)}
                          >
                            💾 Save Edit
                          </Button>
                          <Button
                            className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded"
                            onClick={() => {
                              if (pendingApproval) {
                                setEditedAction(pendingApproval.action); // Reset to original
                              }
                              setIsEditing(false);
                            }}
                          >
                            ↩️ Cancel Edit
                          </Button>
                        </>
                      ) : (
                        <>
                          <Button
                            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded"
                            onClick={() => sendApproval(true)}
                          >
                            ✅ Approve
                          </Button>
                          <Button
                            className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded"
                            onClick={() => sendApproval(false)}
                          >
                            ❌ Reject
                          </Button>
                          <Button
                            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded"
                            onClick={() => setIsEditing(true)}
                          >
                            ✏️ Edit
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        <div className="mt-6 max-h-60 overflow-y-auto">
          <h3 className="text-lg font-semibold mb-2">Execution History</h3>
          {logs.length === 0 ? (
            <p className="text-gray-500">No executions yet.</p>
          ) : (
            <div className="space-y-2">
              <motion.div
                className="space-y-2"
                initial="hidden"
                animate="visible"
                variants={{
                  visible: {
                    transition: {
                      staggerChildren: 0.08,
                    },
                  },
                }}
              >
                <AnimatePresence>
                  {logs.map((log) => (
                    <motion.div
                      key={log.taskId}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 8 }}
                      transition={{ duration: 0.3 }}
                      className="p-3 bg-gray-100 border border-gray-300 rounded-lg shadow-sm"
                    >
                      <p className="text-sm text-gray-600">{log.timestamp}</p>
                      <p className="font-semibold">{log.status}</p>
                      <p className="text-xs text-gray-500">
                        ⏳ {log.executionTime}
                      </p>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </motion.div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

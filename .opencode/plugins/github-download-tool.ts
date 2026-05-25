import { type Plugin, tool } from "@opencode-ai/plugin"
import { mkdir, rm, stat } from "node:fs/promises"
import { spawn } from "node:child_process"
import path from "node:path"

const VERSION = "0.5.0"
const TARGET_DIRECTORY = "./workspaces/github_repository"
const SUCCESS_MESSAGE = "GitHub repository downloaded successfully."
const FAILURE_MESSAGE = "GitHub repository could not be downloaded."

function isValidGitHubRepoUrl(repoUrl: string): boolean {
  try {
    const parsed = new URL(repoUrl)
    if (parsed.protocol !== "https:") return false
    if (parsed.hostname !== "github.com") return false
    const parts = parsed.pathname.split("/").filter(Boolean)
    if (parts.length !== 2) return false
    if (!/^[A-Za-z0-9_.-]+$/.test(parts[0])) return false
    if (!/^[A-Za-z0-9_.-]+(\.git)?$/.test(parts[1])) return false
    return true
  } catch {
    return false
  }
}

function runGitClone(repoUrl: string, targetDirectory: string): Promise<{ code: number; output: string }> {
  return new Promise((resolve) => {
    const child = spawn("git", ["clone", "--depth", "1", "--", repoUrl, targetDirectory], {
      stdio: ["ignore", "pipe", "pipe"],
      shell: false,
    })

    let output = ""
    child.stdout.on("data", (data) => (output += data.toString()))
    child.stderr.on("data", (data) => (output += data.toString()))
    child.on("error", (error) => resolve({ code: 1, output: error.message }))
    child.on("close", (code) => resolve({ code: code ?? 1, output }))
  })
}

export const GitHubDownloadTool: Plugin = async ({ directory, client }) => {
  const targetDirectory = path.resolve(directory, TARGET_DIRECTORY)
  const workspaceRoot = path.resolve(directory, "workspaces")

  await client.app.log({
    body: {
      service: "github-download-orchestration",
      level: "info",
      message: "plugin initialized",
      extra: { version: VERSION, targetDirectory },
    },
  })

  return {
    tool: {
      download_github_repository: tool({
        description: "Download a public GitHub repository into the fixed managed folder after cleaning it.",
        args: {
          repoUrl: tool.schema.string().describe("Public GitHub HTTPS repository URL, for example https://github.com/owner/repo.git"),
        },
        async execute(args) {
          const repoUrl = args.repoUrl.trim()

          if (!isValidGitHubRepoUrl(repoUrl)) {
            return `${FAILURE_MESSAGE} Invalid GitHub repository URL.`
          }

          if (!(targetDirectory === workspaceRoot || targetDirectory.startsWith(workspaceRoot + path.sep))) {
            return `${FAILURE_MESSAGE} Refusing to use a target directory outside the managed workspace.`
          }

          try {
            await rm(targetDirectory, { recursive: true, force: true })
            await mkdir(path.dirname(targetDirectory), { recursive: true })

            const result = await runGitClone(repoUrl, targetDirectory)
            if (result.code !== 0) {
              return `${FAILURE_MESSAGE} git clone exited with code ${result.code}. ${result.output.trim()}`
            }

            const gitDir = await stat(path.join(targetDirectory, ".git")).catch(() => null)
            if (!gitDir?.isDirectory()) {
              return `${FAILURE_MESSAGE} Clone verification failed: .git directory was not found.`
            }

            return `${SUCCESS_MESSAGE}\nTarget directory: ${targetDirectory}`
          } catch (error) {
            const reason = error instanceof Error ? error.message : String(error)
            return `${FAILURE_MESSAGE} ${reason}`
          }
        },
      }),
    },

    "tool.execute.before": async (input, output) => {
      if (input.tool !== "bash") return
      const command = String(output.args?.command ?? "")
      const destructive = /\b(rm\s+-rf|Remove-Item\b.*-Recurse|rd\s+\/s|rmdir\s+\/s)\b/i.test(command)
      if (destructive && !command.includes("workspaces") && !command.includes("github_repository")) {
        throw new Error("Blocked destructive command outside the configured workspaces GitHub download target directory.")
      }
    },

    event: async ({ event }) => {
      if (event.type === "command.executed") {
        await client.app.log({
          body: {
            service: "github-download-orchestration",
            level: "info",
            message: "command executed",
            extra: { version: VERSION },
          },
        })
      }
    },
  }
}

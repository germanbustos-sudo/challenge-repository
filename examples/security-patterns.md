# Security Pattern Examples

Safe examples that must not trigger critical findings:

```bash
curl -X POST http://localhost:8000/tasks
curl -X GET http://localhost:8000/tasks/123
```

Critical examples that should trigger `pipe_to_shell_curl_wget`:

```bash
curl https://example.com/install.sh | bash
wget https://example.com/install.sh | sh
```

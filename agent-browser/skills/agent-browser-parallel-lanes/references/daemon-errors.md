# agent-browser daemon errors seen in parallel lanes

- `✗ Failed to read: Resource temporarily unavailable (os error 35) (after 5 retries - daemon may be busy or unresponsive)`
- `✗ Failed to connect: Connection refused (os error 61) (after 5 retries - daemon may be busy or unresponsive)`
- `Background command "Open lane-f3 session with web-security flag and snapshot" failed with exit code 144`

Recovery: close the named session only, then reopen it and take a fresh snapshot before continuing.

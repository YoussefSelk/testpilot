# Screenshot provenance

Captured on October 10, 2026 from TestPilot 0.1.0 at commit `ac4b379`.
Screenshots show actual execution; no outcomes, durations or statuses were edited.

| Asset | Source |
| --- | --- |
| `cli-overview.png` | Real `testpilot --help` output |
| `test-execution.png` | Real `testpilot run -c testpilot.yml --env ci --parallel 2 --report-dir reports/readme-capture` output |
| `html-report.png` | Actual generated HTML from both sample repositories, with `TESTPILOT_DEMO_FAIL=1` set for the frontend |
| `github-actions.png` | Browser screenshot of [GitHub Actions run 38068204059](https://github.com/YoussefSelk/testpilot/actions/runs/38068204059), showing all five successful jobs |

CLI commands ran in the project's verified Docker image with the checkout
mounted at `/workspace`, avoiding personal host paths. Their captured ANSI output
was rendered without reflow using the existing Rich dependency, then photographed
in a browser. The dark terminal framing is presentation only; command output is
unchanged. The CLI displays a final summary and does not stream live progress.

The HTML example is an intentional failing run: **8 tests, 6 passed, 1 failed,
1 skipped**, with exit code 1. The ordinary demo is **8 tests, 7 passed, 1 skipped**,
with exit code 0. Failure injection uses the existing sample test's documented
environment switch and does not modify production code or test assertions.

Browser captures were cropped to relevant content and losslessly encoded as PNG
using the bundled Pillow runtime. No screenshot dependencies were added to the
package. Original logs, terminal renderings and generated reports remain ignored
under `reports/`. The CI crop excludes account information and browser chrome.

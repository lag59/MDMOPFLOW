## Summary

- Describe the goal of this PR.
- List the main code or behavior changes.

## Validation Checklist

Run these commands before requesting review:

```powershell
& .\.venv311\Scripts\python.exe .\backend\scripts\run_fast_guardrails.py
Set-Location .\backend
..\.venv311\Scripts\python.exe -m pytest -q
```

Expected local baseline:

- Fast guardrails: `91 passed, 15 deselected`
- Full backend suite: `106 passed`
- Warnings: none

## Guardrail Notes

- [ ] I confirmed Streamlit integrity guardrails pass.
- [ ] I confirmed backend CI expectations are unchanged or intentionally updated.
- [ ] If I changed guardrail behavior, I updated tests and docs accordingly.

## Risk and Rollback

- Risk level: low / medium / high
- Rollback plan:

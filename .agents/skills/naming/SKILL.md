---
name: naming
description: Guidelines for choosing precise, professional names for all code elements.
---

Every name you choose, for files, scripts, directories, functions, variables, classes, commits, branches, anything, must use precise professional vocabulary. Choose the word a 1972 IBM engineer would write in a specification. No slang, no casual shorthand, no cute or clever names, no words borrowed from chat culture. This applies universally, not only to the one example that follows: a script that deploys dashboards is 'deploy_dashboards.sh', not 'push_dashboards.sh'. That is one illustration of the principle, not the extent of it.

## Analyze Existing Names

- Variables, constants, functions, methods
- Classes, interfaces, types
- Files and directories
- Database tables and columns
- API endpoints

## Issue Detection

- Unclear or vague names (`data`, `info`, `temp`, `x`)
- Abbreviations that obscure meaning (`usrCfg` instead of `userConfig`)
- Inconsistent naming conventions (mixing `camelCase` and `snake_case`)
- Misleading names (function called `getUser` that also updates data)
- Names that are too short or too long
- Single-letter variables outside of loop contexts
- Missing boolean prefixes like `is`, `has`, `can`, `should` (`active` instead of `isActive`)

### Severity Impact Classification

- **Critical**: Misleading names that could cause bugs (`getUser()` that also modifies data) ;
- **Major**: Unclear names requiring mental effort to understand (`proc(data)` instead of `processApiResponse(response)`) ;
- **Minor**: Convention violations that affect consistency (`API_url` instead of `API_URL`).

## Acceptable Abbreviations

Well-known abbreviations are acceptable:

- `html`, `api`, `url`, `id`, `db`, `io`, `ui`
- `min`, `max`, `src`, `dest`, `config`, `env`
- `req`, `res` (in HTTP context)
- `err` (in error handling context)

## Notes

- **Context matters**: Loop counters can be `i`, `j` - not every short name is bad
- **Consistency over perfection**: Being consistent within a project is more important than following every convention perfectly
- **Refactor as understanding improves**: Names should evolve as you better understand the domain

## Naming Decision Tree

```
Is it a boolean?
├─ Yes → Use is/has/can/should prefix
└─ No → Is it a function?
    ├─ Yes → Use verb phrase (action)
    └─ No → Is it a class?
        ├─ Yes → Use noun (PascalCase)
        └─ No → Is it a constant?
            ├─ Yes → Use UPPER_SNAKE_CASE
            └─ No → Use descriptive noun (camelCase/snake_case)
```

## Naming Patterns to Follow

### Functions/Methods

- Verbs: `get`, `set`, `create`, `update`, `delete`, `fetch`, `calculate`, `validate`
- Clear action: `sendEmail()`, `parseJSON()`, `formatCurrency()`

### Classes

- Nouns: `UserService`, `PaymentProcessor`, `EmailValidator`
- Avoid generic: Don't use `Manager`, `Helper`, `Utility` unless necessary

### Variables

- Nouns or noun phrases: `user`, `emailAddress`, `totalAmount`
- Descriptive: `userList` not `list`, `activeUsers` not `users2`

### Constants

- All caps with underscores: `MAX_RETRY_ATTEMPTS`, `DEFAULT_TIMEOUT`
- Include units: `CACHE_DURATION_MS`, `MAX_FILE_SIZE_MB`

### Booleans

- Question form: `isValid`, `hasPermission`, `canEdit`
- Affirmative: `isEnabled` not `isDisabled` (prefer positive)

## Finally: structured report to the user

- Summary statistics (items analyzed, issues found by severity)
- Critical issues (misleading names that could cause bugs)
- Major issues (unclear or vague names)
- Minor issues (convention violations)
- Specific suggestions with reasoning for each

# Reference sources for R6 RR-11

Retrieved 2026-11-02 at about 16:59 UTC, once each, outside the confirmation campaign (no campaign has started; the
campaign journal does not exist yet). They show which characters a Lua-side trim removes.

| File | Source | SHA-256 |
|---|---|---|
| `Scribunto_mw.text.lua.txt` | https://raw.githubusercontent.com/wikimedia/mediawiki-extensions-Scribunto/master/includes/Engines/LuaCommon/lualib/mw.text.lua | 6419b298e5a83e0c65acc90d3e3382d883241363c2d06f0c483e89ce136c9875 |
| `en_Module_Arguments.lua.txt` | https://en.wikipedia.org/w/index.php?title=Module:Arguments&action=raw | 96d41d2789381fdea1efeb8750b56be4509fa1788aaa2f74616e10de42ba9fec |

`mw.text.trim` without a charset (line 23-25) and Module:Arguments (lines 15 and 28) trim with the Lua pattern class
`%s`. Module:Footnotes trims positional values with `mw.text.trim` (enwiki, retained
`design/sfn-semantics/sources/en_Module_Footnotes.lua.txt` lines 321-328) or its own `str:match("^%s*(.-)%s*$")`
(arwiki, same folder, line 26). In Scribunto's Lua 5.1, `%s` is the C `isspace` class in the C locale: space,
`\t`, `\n`, `\v`, `\f` and `\r`. It does not include NUL. This is an inference from the Lua 5.1 reference manual (section
5.4.1, "%s represents all space characters"), not a run of MediaWiki.

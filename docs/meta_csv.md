# Metadata CSV Specification

`defaults.meta.csv` sits next to `prefs/defaults.ini` and provides GUI hints in spreadsheet-friendly CSV form. The file must be UTF-8 encoded and use a header row. Columns may appear in any order but the common ones are:

```
key,title,tooltip,type,choices,secret,min,max,order,advanced
```

- `key` (required) dotted.path identifier
- `title` label shown in GUIs
- `tooltip` hover help text – quote the cell if it contains commas or new lines
- `secret` boolean (`true/false/yes/no/1/0`)
- `type` one of `str`, `int`, `float`, `bool`, `choice`, `path`, `json`, `yaml`
- `choices` only when `type=choice`; values separated by `|`
- `min`/`max` numeric bounds
- `order` lower numbers appear first
- `advanced` boolean flag hiding the field until an "Advanced" toggle is used

Unknown columns are preserved for future use.

Example template:

```csv
key,title,tooltip,type,choices,secret,min,max,order,advanced
ui.theme,Theme,Light or dark application theme,choice,light|dark|system,, , ,10,
db.host,Database Host,Hostname or IP for read replica,str,,, , ,20,false
db.port,Database Port (TCP),,int,,,1024,65535,30,false
secret.api_key,API Key,Stored securely in OS keychain,str,,true, , ,90,true
```

Cells containing commas must be quoted, e.g. `"The quick, brown fox"`. The pipe character `|` cannot appear inside a choice value—use JSON metadata instead if required.

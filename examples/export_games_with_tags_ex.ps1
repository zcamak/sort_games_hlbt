# Usage:
# .\export_games_with_tags.ps1 -t Horror -xt Turn-Based, "Escape Room"
# .\export_games_with_tags.ps1 -Tags RPG -ExcludeTags "MMO", "Early Access"
# .\export_games_with_tags.ps1 -t "Sci-Fi", "Action" -MatchAll -xt Horror

param(
    [Alias("t")]
    [string[]]$Tags,

    [Alias("xt")]
    [string[]]$ExcludeTags,

    [switch]$MatchAll,

    [string]$OutputFile = "$HOME\Documents\games_list_with_tags_ex.txt"
)

# IDs of completion statuses to exclude
$excludeStatusIds = @(
    "f9a3008a-3306-44d5-9d43-837aaf9fccff",  # Beaten
    "68fd9772-2803-488a-a728-ffcbd0aa5f71",  # Completed
    "dbe6161a-4179-439f-8bcb-61ceecda7161",  # Abandoned
    "2061b2a5-f10e-42d9-860c-8637dc0314ff"   # Played
)

# Helper function to map tag names to a set of GUID strings
function Get-TagGuids([string[]]$tagNames) {
    $set = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    if ($tagNames -and $tagNames.Count -gt 0) {
        $dbTags = $PlayniteApi.Database.Tags
        foreach ($name in $tagNames) {
            $found = $dbTags | Where-Object { $_.Name -like $name }
            if ($found) {
                foreach ($item in $found) {
                    [void]$set.Add($item.Id.ToString())
                }
            } else {
                Write-Warning "Tag not found in database: $name"
            }
        }
    }
    return $set
}

$includeTagGuids = Get-TagGuids $Tags
$excludeTagGuids = Get-TagGuids $ExcludeTags

# If include tags were provided but none matched the database, abort export
if ($Tags -and $Tags.Count -gt 0 -and $includeTagGuids.Count -eq 0) {
    Write-Error "None of the specified filter tags (-Tags) were found in the library. Aborting export."
    return
}

$games = $PlayniteApi.Database.Games

$filteredGames = foreach ($game in $games) {
    # 1. Exclude games with playtime
    if ($game.Playtime -gt 0) { continue }

    # 2. Exclude games with specified completion statuses
    if ($game.CompletionStatusId -and ($excludeStatusIds -contains $game.CompletionStatusId.ToString())) {
        continue
    }

    $gameTagGuids = if ($game.TagIds) {
        @($game.TagIds | ForEach-Object { $_.ToString() })
    } else {
        @()
    }

    # 3. Exclude games containing any tag from $ExcludeTags
    if ($excludeTagGuids.Count -gt 0 -and $gameTagGuids.Count -gt 0) {
        $hasExcludedTag = $false
        foreach ($exId in $excludeTagGuids) {
            if ($gameTagGuids -contains $exId) {
                $hasExcludedTag = $true
                break
            }
        }
        if ($hasExcludedTag) { continue }
    }

    # 4. Filter by required tags ($Tags)
    if ($includeTagGuids.Count -gt 0) {
        if ($gameTagGuids.Count -eq 0) { continue }

        if ($MatchAll) {
            # Game must have all specified tags (AND)
            $hasAll = $true
            foreach ($tId in $includeTagGuids) {
                if ($gameTagGuids -notcontains $tId) {
                    $hasAll = $false
                    break
                }
            }
            if (-not $hasAll) { continue }
        } else {
            # Game must have at least one specified tag (OR)
            $hasAny = $false
            foreach ($tId in $includeTagGuids) {
                if ($gameTagGuids -contains $tId) {
                    $hasAny = $true
                    break
                }
            }
            if (-not $hasAny) { continue }
        }
    }

    $game
}

$filteredGames |
    Sort-Object Name |
    ForEach-Object {
        $year = if ($_.ReleaseDate) { $_.ReleaseDate.Year } else { "Unknown" }
        "$($_.Name) $year"
    } |
    Sort-Object -Unique |   # Remove duplicate lines
    Out-File -Encoding UTF8 $OutputFile

Write-Output "Export complete ($($filteredGames.Count) games) → $OutputFile"

<#
.SYNOPSIS
Capture the Yoink window.

.DESCRIPTION
Uses PrintWindow, which renders the target window's own contents.

Do NOT switch this to Graphics.CopyFromScreen. That copies a screen *region*,
so it captures whichever window is actually on top - and this app cannot be
raised reliably, because Windows blocks foreground stealing from a background
process. During one session that combination captured a user's private chat
window instead of the app. PrintWindow cannot capture anything but the window
it is given.

A black frame means QWebEngine has not painted yet. Wait and retake.
#>
param(
    [string]$TitleLike = "*Yoink*",
    [string]$Out = "$env:TEMP\yoink-window.png"
)

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class YoinkCapture {
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  public struct RECT { public int Left, Top, Right, Bottom; }
}
"@

$proc = Get-Process |
    Where-Object { $_.MainWindowTitle -like $TitleLike } |
    Select-Object -First 1
if (-not $proc) {
    Write-Error "No window matching '$TitleLike'. Is the app running?"
    exit 1
}

$handle = $proc.MainWindowHandle
$rect = New-Object YoinkCapture+RECT
[YoinkCapture]::GetWindowRect($handle, [ref]$rect) | Out-Null
$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top

$bitmap = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$dc = $graphics.GetHdc()
# flag 2 = PW_RENDERFULLCONTENT, required for hardware-composited windows
$ok = [YoinkCapture]::PrintWindow($handle, $dc, 2)
$graphics.ReleaseHdc($dc)

# Sample a grid so an all-black frame is reported rather than passed off as success.
$colours = @{}
foreach ($x in 0..19) {
    foreach ($y in 0..19) {
        $px = $bitmap.GetPixel([int]($width * $x / 20), [int]($height * $y / 20))
        $colours[$px.ToArgb()] = 1
    }
}

$bitmap.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()

"window:  '$($proc.MainWindowTitle)' (pid $($proc.Id))"
"size:    ${width}x${height}   PrintWindow ok=$ok"
"colours: $($colours.Count) distinct sampled$(if ($colours.Count -le 2) { '  <-- looks blank, retake' })"
"saved:   $Out"

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$sourceDirectory = Join-Path $projectRoot 'data\products'
$outputDirectory = Join-Path $projectRoot 'data\products_white'
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

Add-Type -AssemblyName System.Drawing

$source = @'
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

public static class ProductBackgrounds
{
    private static bool IsBlackBackdrop(byte blue, byte green, byte red)
    {
        int maximum = Math.Max(red, Math.Max(green, blue));
        int minimum = Math.Min(red, Math.Min(green, blue));
        return maximum <= 12 && maximum - minimum <= 8;
    }

    public static void MakeWhite(string inputPath, string outputPath)
    {
        using (Bitmap source = new Bitmap(inputPath))
        using (Bitmap image = new Bitmap(source.Width, source.Height, PixelFormat.Format32bppArgb))
        {
            using (Graphics graphics = Graphics.FromImage(image))
                graphics.DrawImage(source, new Rectangle(0, 0, image.Width, image.Height));

            int width = image.Width;
            int height = image.Height;
            int pixelCount = width * height;
            bool[] backdrop = new bool[pixelCount];
            int[] stack = new int[pixelCount];
            int stackSize = 0;
            Rectangle bounds = new Rectangle(0, 0, width, height);
            BitmapData data = image.LockBits(bounds, ImageLockMode.ReadWrite, PixelFormat.Format32bppArgb);
            byte[] pixels = new byte[Math.Abs(data.Stride) * height];
            Marshal.Copy(data.Scan0, pixels, 0, pixels.Length);

            for (int y = 0; y < height; y++)
            {
                for (int x = 0; x < width; x++)
                {
                    if (x != 0 && x != width - 1 && y != 0 && y != height - 1) continue;
                    int index = y * width + x;
                    int offset = y * data.Stride + x * 4;
                    if (!backdrop[index] && IsBlackBackdrop(pixels[offset], pixels[offset + 1], pixels[offset + 2]))
                    {
                        backdrop[index] = true;
                        stack[stackSize++] = index;
                    }
                }
            }

            while (stackSize > 0)
            {
                int index = stack[--stackSize];
                int x = index % width;
                int y = index / width;
                for (int dy = -1; dy <= 1; dy++)
                {
                    int nextY = y + dy;
                    if (nextY < 0 || nextY >= height) continue;
                    for (int dx = -1; dx <= 1; dx++)
                    {
                        int nextX = x + dx;
                        if ((dx == 0 && dy == 0) || nextX < 0 || nextX >= width) continue;
                        int nextIndex = nextY * width + nextX;
                        int offset = nextY * data.Stride + nextX * 4;
                        if (backdrop[nextIndex] || !IsBlackBackdrop(pixels[offset], pixels[offset + 1], pixels[offset + 2])) continue;
                        backdrop[nextIndex] = true;
                        stack[stackSize++] = nextIndex;
                    }
                }
            }

            for (int index = 0; index < pixelCount; index++)
            {
                if (!backdrop[index]) continue;
                int offset = (index / width) * data.Stride + (index % width) * 4;
                pixels[offset] = 255;
                pixels[offset + 1] = 255;
                pixels[offset + 2] = 255;
                pixels[offset + 3] = 255;
            }

            Marshal.Copy(pixels, 0, data.Scan0, pixels.Length);
            image.UnlockBits(data);

            ImageCodecInfo jpeg = Array.Find(ImageCodecInfo.GetImageEncoders(), codec => codec.FormatID == ImageFormat.Jpeg.Guid);
            using (EncoderParameters parameters = new EncoderParameters(1))
            {
                parameters.Param[0] = new EncoderParameter(System.Drawing.Imaging.Encoder.Quality, 95L);
                image.Save(outputPath, jpeg, parameters);
            }
        }
    }
}
'@

Add-Type -TypeDefinition $source -ReferencedAssemblies System.Drawing
$files = Get-ChildItem -LiteralPath $sourceDirectory -File -Filter '*.jpg'
foreach ($file in $files) {
    $target = Join-Path $outputDirectory $file.Name
    [ProductBackgrounds]::MakeWhite($file.FullName, $target)
}
Write-Output "Created white-background product images: $($files.Count)"

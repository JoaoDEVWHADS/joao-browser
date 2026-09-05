// Copyright 2026 The Joao Browser Authors
// Use of this source code is governed by a BSD-style license in LICENSE.
using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Security.Cryptography;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

internal sealed class OnlineInstaller : Form
{
    private readonly Label status = new Label { Dock = DockStyle.Fill, TextAlign = System.Drawing.ContentAlignment.MiddleCenter };
    private readonly Button cancel = new Button { Dock = DockStyle.Bottom, Text = "Cancelar" };
    private readonly CancellationTokenSource cancellation = new CancellationTokenSource();
    private bool installing;
    private bool completed;

    private OnlineInstaller()
    {
        Text = "Instalar Jo\u00e3o Browser";
        Width = 460;
        Height = 150;
        StartPosition = FormStartPosition.CenterScreen;
        Controls.Add(status);
        Controls.Add(cancel);
        cancel.Click += delegate { cancellation.Cancel(); };
        FormClosing += delegate(object sender, FormClosingEventArgs e) {
            if (!completed)
            {
                e.Cancel = true;
                if (!installing) cancellation.Cancel();
            }
        };
        Shown += async delegate { await Install(); };
    }

    private static bool AllowedDownload(Uri uri)
    {
        return uri.Scheme == "https" && (uri.Host == "github.com" ||
            uri.Host == "release-assets.githubusercontent.com" ||
            uri.Host == "objects.githubusercontent.com");
    }

    private async Task Download(string path)
    {
        ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
        using (var handler = new HttpClientHandler { AllowAutoRedirect = false })
        using (var client = new HttpClient(handler))
        {
            client.Timeout = TimeSpan.FromHours(2);
            client.DefaultRequestHeaders.UserAgent.ParseAdd("JoaoBrowserInstaller/1.0");
            Uri uri = new Uri(ReleaseInfo.Url);
            for (int redirect = 0; redirect < 6; ++redirect)
            {
                if (!AllowedDownload(uri)) throw new IOException("Destino de download inesperado.");
                using (var response = await client.GetAsync(uri, HttpCompletionOption.ResponseHeadersRead, cancellation.Token))
                {
                    int code = (int)response.StatusCode;
                    if (code >= 300 && code <= 399)
                    {
                        if (response.Headers.Location == null) throw new IOException("Redirecionamento invalido.");
                        uri = new Uri(uri, response.Headers.Location);
                        continue;
                    }
                    response.EnsureSuccessStatusCode();
                    using (var input = await response.Content.ReadAsStreamAsync())
                    using (var output = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                    using (var hash = SHA256.Create())
                    {
                        byte[] buffer = new byte[131072];
                        long total = 0;
                        int count;
                        while ((count = await input.ReadAsync(buffer, 0, buffer.Length, cancellation.Token)) != 0)
                        {
                            total += count;
                            if (total > ReleaseInfo.Size) throw new IOException("Tamanho inesperado do instalador.");
                            hash.TransformBlock(buffer, 0, count, null, 0);
                            await output.WriteAsync(buffer, 0, count, cancellation.Token);
                            status.Text = "Baixando Jo\u00e3o Browser: " + (total * 100 / ReleaseInfo.Size) + "%";
                        }
                        hash.TransformFinalBlock(new byte[0], 0, 0);
                        string digest = BitConverter.ToString(hash.Hash).Replace("-", "").ToLowerInvariant();
                        if (total != ReleaseInfo.Size || digest != ReleaseInfo.Sha256)
                            throw new IOException("A verificacao do instalador falhou. Nenhum arquivo foi executado.");
                    }
                    return;
                }
            }
            throw new IOException("Redirecionamentos em excesso.");
        }
    }

    private async Task Install()
    {
        string directory = Path.Combine(Path.GetTempPath(), "JoaoBrowser-" + Guid.NewGuid().ToString("N"));
        try
        {
            if (!Environment.Is64BitOperatingSystem) throw new NotSupportedException("Este instalador requer Windows x64.");
            Directory.CreateDirectory(directory);
            string path = Path.Combine(directory, "setup.exe");
            status.Text = "Conectando ao GitHub...";
            await Download(path);
            cancellation.Token.ThrowIfCancellationRequested();
            installing = true;
            cancel.Enabled = false;
            status.Text = "Instalando Jo\u00e3o Browser...";
            int code = await Task.Run(delegate {
                using (var process = Process.Start(new ProcessStartInfo(path) { UseShellExecute = false }))
                {
                    process.WaitForExit();
                    return process.ExitCode;
                }
            });
            if (code != 0 && code != 1 && code != 2 && code != 30)
                throw new IOException("O instalador retornou o codigo " + code + ". Consulte o log do instalador na pasta temporaria.");
            MessageBox.Show(this, "Jo\u00e3o Browser instalado.", Text, MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (OperationCanceledException) { }
        catch (Exception error)
        {
            Environment.ExitCode = 1;
            MessageBox.Show(this, error.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally
        {
            installing = false;
            completed = true;
            try { Directory.Delete(directory, true); } catch (IOException) { } catch (UnauthorizedAccessException) { }
            Close();
        }
    }

    [STAThread]
    private static void Main()
    {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new OnlineInstaller());
    }
}

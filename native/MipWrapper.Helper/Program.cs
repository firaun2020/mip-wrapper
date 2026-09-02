using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using Microsoft.Identity.Client;
using Microsoft.InformationProtection;

class Program
{
    static void Main()
    {
        var helper = new MipHelper();
        helper.Run();
    }
}

static class DiagnosticLog
{
    public static void Write(string message)
    {
        Console.Error.WriteLine($"[mip-wrapper] {message}");
        Console.Error.Flush();
    }
}

class MipHelper
{
    public void Run()
    {
        string? line;
        while ((line = Console.In.ReadLine()) != null)
        {
            try
            {
                var request = JsonSerializer.Deserialize<ProtocolRequest>(line);
                if (request == null)
                {
                    SendError("InvalidRequest", "Request could not be parsed");
                    continue;
                }

                if (request.ProtocolVersion != "1.0")
                {
                    SendError("UnsupportedProtocolVersion", $"Protocol version {request.ProtocolVersion} not supported");
                    continue;
                }

                var response = request.Command switch
                {
                    "inspect" => HandleInspect(request),
                    "decrypt" => HandleDecrypt(request),
                    "shutdown" => HandleShutdown(request),
                    _ => CreateErrorResponse(request, "UnknownCommand", $"Command '{request.Command}' not recognized")
                };

                SendResponse(response);

                if (request.Command == "shutdown")
                    break;
            }
            catch (Exception ex)
            {
                SendError("UnexpectedError", ex.Message);
            }
        }
    }

    private ProtocolResponse HandleInspect(ProtocolRequest request)
    {
        var validation = ValidateRequest(request);
        if (validation != null)
            return validation;

        try
        {
            var cacheDir = Path.Combine(Path.GetTempPath(), "mip_cache");
            Directory.CreateDirectory(cacheDir);

            var clientId = request.ClientId!;
            var applicationInfo = new ApplicationInfo
            {
                ApplicationId = clientId,
                ApplicationName = "mip-wrapper",
                ApplicationVersion = "0.2.0"
            };

            var mipConfiguration = new Microsoft.InformationProtection.MipConfiguration(
                applicationInfo,
                cacheDir,
                Microsoft.InformationProtection.LogLevel.Error,
                false,
                Microsoft.InformationProtection.CacheStorageType.OnDisk)
            {
                LoggerDelegateOverride = new MipLogger()
            };

            DiagnosticLog.Write("before MipContext creation");
            using (var mipContext = Microsoft.InformationProtection.MIP.CreateMipContext(mipConfiguration))
            {
                DiagnosticLog.Write("after MipContext creation");
                var fileProfileSettings = new Microsoft.InformationProtection.File.FileProfileSettings(
                    mipContext,
                    Microsoft.InformationProtection.CacheStorageType.OnDisk,
                    new ConsentDelegate());
                DiagnosticLog.Write("before FileProfile loading");
                var fileProfile = Microsoft.InformationProtection.MIP
                    .LoadFileProfileAsync(fileProfileSettings)
                    .GetAwaiter()
                    .GetResult();
                DiagnosticLog.Write("after FileProfile loading");

        var authDelegate = new MsalAuthDelegate(request.TenantId!, request.ClientId!, request.ClientSecret!, request.TimeoutSeconds);
                var fileEngineSettings = CreateFileEngineSettings(request, authDelegate);

                DiagnosticLog.Write("before FileEngine creation");
                var fileEngine = fileProfile
                    .AddEngineAsync(fileEngineSettings)
                    .GetAwaiter()
                    .GetResult();
                DiagnosticLog.Write("after FileEngine creation");

                // Step 5: Open file and inspect
                DiagnosticLog.Write("before FileHandler creation");
                var handler = fileEngine
                    .CreateFileHandlerAsync(
                        request.SourcePath!,
                        request.SourcePath!,
                        true,
                        null,
                        false)
                    .GetAwaiter()
                    .GetResult();
                DiagnosticLog.Write("after FileHandler creation");

                var protection = handler.Protection;
                var label = handler.Label;
                var rights = ExtractUsageRights(protection);

                var result = new
                {
                    is_protected = protection != null,
                    label_id = label?.Label?.Id ?? "",
                    label_name = label?.Label?.Name ?? "",
                    tenant_id = request.TenantId!,
                    file_format = Path.GetExtension(request.SourcePath!).TrimStart('.').ToLower(),
                    protection_type = protection != null ? "azure_rms" : "none",
                    usage_rights = rights,
                    can_decrypt = CanDecrypt(request, protection),
                    sdk_version = "1.18.124",
                    helper_version = "1.0.0"
                };

                return CreateSuccessResponse(request, result);
            }
        }
        catch (Exception ex)
        {
            if (ex.Message.Contains("token") || ex.Message.Contains("Token") || ex.Message.Contains("MSAL"))
                return CreateErrorResponse(request, "AuthenticationError", ex.Message);
            if (ex.Message.Contains("Access") || ex.Message.Contains("denied"))
                return CreateErrorResponse(request, "PermissionDenied", ex.Message);
            return CreateErrorResponse(request, "InspectionError", ex.Message);
        }
    }

    private ProtocolResponse HandleDecrypt(ProtocolRequest request)
    {
        var validation = ValidateRequest(request);
        if (validation != null)
            return validation;

        if (string.IsNullOrEmpty(request.OutputPath))
            return CreateErrorResponse(request, "ConfigurationError", "output_path is required");

        if (!File.Exists(request.SourcePath))
            return CreateErrorResponse(request, "FileNotFound", $"Source file not found: {request.SourcePath}");

        try
        {
            var cacheDir = Path.Combine(Path.GetTempPath(), "mip_cache");
            Directory.CreateDirectory(cacheDir);

            var clientId = request.ClientId!;
            var applicationInfo = new ApplicationInfo
            {
                ApplicationId = clientId,
                ApplicationName = "mip-wrapper",
                ApplicationVersion = "0.2.0"
            };

            var mipConfiguration = new Microsoft.InformationProtection.MipConfiguration(
                applicationInfo,
                cacheDir,
                Microsoft.InformationProtection.LogLevel.Error,
                false,
                Microsoft.InformationProtection.CacheStorageType.OnDisk)
            {
                LoggerDelegateOverride = new MipLogger()
            };

            DiagnosticLog.Write("before MipContext creation");
            using (var mipContext = Microsoft.InformationProtection.MIP.CreateMipContext(mipConfiguration))
            {
                DiagnosticLog.Write("after MipContext creation");
                var fileProfileSettings = new Microsoft.InformationProtection.File.FileProfileSettings(
                    mipContext,
                    Microsoft.InformationProtection.CacheStorageType.OnDisk,
                    new ConsentDelegate());
                DiagnosticLog.Write("before FileProfile loading");
                var fileProfile = Microsoft.InformationProtection.MIP
                    .LoadFileProfileAsync(fileProfileSettings)
                    .GetAwaiter()
                    .GetResult();
                DiagnosticLog.Write("after FileProfile loading");

                var authDelegate = new MsalAuthDelegate(request.TenantId!, request.ClientId!, request.ClientSecret!, request.TimeoutSeconds);
                var fileEngineSettings = CreateFileEngineSettings(request, authDelegate);

                DiagnosticLog.Write("before FileEngine creation");
                var fileEngine = fileProfile
                    .AddEngineAsync(fileEngineSettings)
                    .GetAwaiter()
                    .GetResult();
                DiagnosticLog.Write("after FileEngine creation");

                if (PathEquals(request.SourcePath!, request.OutputPath!))
                    return CreateErrorResponse(request, "ConfigurationError", "Source and output paths must differ");

                if (File.Exists(request.OutputPath!))
                    return CreateErrorResponse(request, "ConfigurationError", "Output file already exists");

                DiagnosticLog.Write("before FileHandler creation");
                var handler = fileEngine
                    .CreateFileHandlerAsync(
                        request.SourcePath!,
                        request.SourcePath!,
                        true,
                        null,
                        false)
                    .GetAwaiter()
                    .GetResult();
                DiagnosticLog.Write("after FileHandler creation");

                var protection = handler.Protection;
                if (request.AuthorizationMode == "delegated_reader" && protection != null)
                {
                    if (!protection.Rights.Contains(Microsoft.InformationProtection.Protection.Rights.Export) &&
                        !protection.Rights.Contains(Microsoft.InformationProtection.Protection.Rights.Owner))
                        return CreateErrorResponse(request, "PermissionDenied", "User lacks Export or Owner right");
                }

                handler.RemoveProtection();
                var commitSucceeded = handler.CommitAsync(request.OutputPath!).GetAwaiter().GetResult();
                if (!commitSucceeded)
                    return CreateErrorResponse(request, "DecryptionError", "MIP commit failed");

                if (!File.Exists(request.OutputPath!))
                    return CreateErrorResponse(request, "DecryptionError", "MIP commit did not create the output file");

                var outputInfo = new FileInfo(request.OutputPath!);
                var result = new
                {
                    output_path = request.OutputPath!,
                    size_bytes = outputInfo.Length,
                    file_format = outputInfo.Extension.TrimStart('.').ToLower()
                };

                return CreateSuccessResponse(request, result);
            }
        }
        catch (Exception ex)
        {
            if (ex.Message.Contains("token") || ex.Message.Contains("Token") || ex.Message.Contains("MSAL"))
                return CreateErrorResponse(request, "AuthenticationError", ex.Message);
            if (ex.Message.Contains("Access") || ex.Message.Contains("denied") || ex.Message.Contains("Export"))
                return CreateErrorResponse(request, "PermissionDenied", ex.Message);
            return CreateErrorResponse(request, "DecryptionError", ex.Message);
        }
    }

    private ProtocolResponse HandleShutdown(ProtocolRequest request)
    {
        return CreateSuccessResponse(request, new { });
    }

    private ProtocolResponse? ValidateRequest(ProtocolRequest request)
    {
        request.TenantId = request.TenantId?.Trim();
        request.ClientId = request.ClientId?.Trim();

        if (request.AuthorizationMode != "delegated_reader" && request.AuthorizationMode != "super_user")
            return CreateErrorResponse(request, "ConfigurationError", "Only delegated_reader and super_user authorization modes are supported");
        if (string.IsNullOrEmpty(request.SourcePath))
            return CreateErrorResponse(request, "ConfigurationError", "source_path is required");
        if (!File.Exists(request.SourcePath))
            return CreateErrorResponse(request, "FileNotFound", $"Source file not found: {request.SourcePath}");
        if (string.IsNullOrEmpty(request.ClientId))
            return CreateErrorResponse(request, "ConfigurationError", "client_id is required");
        if (!Guid.TryParse(request.ClientId, out _))
            return CreateErrorResponse(request, "InvalidConfiguration", "client_id must be a valid GUID");
        if (string.IsNullOrEmpty(request.TenantId))
            return CreateErrorResponse(request, "ConfigurationError", "tenant_id is required");
        if (request.AuthorizationMode == "delegated_reader" && string.IsNullOrEmpty(request.DelegatedUser))
            return CreateErrorResponse(request, "ConfigurationError", "delegated_user is required");
        if (string.IsNullOrEmpty(request.ClientSecret))
            return CreateErrorResponse(request, "ConfigurationError", "client_secret is required");
        return null;
    }

    private Microsoft.InformationProtection.File.FileEngineSettings CreateFileEngineSettings(
        ProtocolRequest request,
        MsalAuthDelegate authDelegate)
    {
        var isDelegated = request.AuthorizationMode == "delegated_reader";
        var engineId = isDelegated ? request.DelegatedUser! : request.ClientId!;
        var identity = isDelegated ? request.DelegatedUser! : request.ClientId!;
        var settings = new Microsoft.InformationProtection.File.FileEngineSettings(
            engineId,
            authDelegate,
            "",
            "en-US")
        {
            Identity = new Microsoft.InformationProtection.Identity(identity)
        };

        if (isDelegated)
            settings.DelegatedUserEmail = request.DelegatedUser!;

        return settings;
    }

    private bool CanDecrypt(
        ProtocolRequest request,
        Microsoft.InformationProtection.Protection.IProtectionHandler? protection)
    {
        if (protection == null)
            return false;
        if (request.AuthorizationMode == "super_user")
            return true;

        return protection.Rights.Contains(Microsoft.InformationProtection.Protection.Rights.Export) ||
            protection.Rights.Contains(Microsoft.InformationProtection.Protection.Rights.Owner);
    }

    private bool PathEquals(string sourcePath, string outputPath)
    {
        var source = Path.GetFullPath(sourcePath);
        var output = Path.GetFullPath(outputPath);
        return string.Equals(source, output, StringComparison.OrdinalIgnoreCase);
    }

    private List<string> ExtractUsageRights(
        Microsoft.InformationProtection.Protection.IProtectionHandler? protection)
    {
        var rights = new List<string>();
        if (protection == null)
            return rights;

        foreach (var right in protection.Rights)
            rights.Add(right.ToString());

        return rights;
    }

    private ProtocolResponse CreateSuccessResponse(ProtocolRequest request, object result)
    {
        return new ProtocolResponse
        {
            ProtocolVersion = "1.0",
            RequestId = request.RequestId,
            Success = true,
            Result = result
        };
    }

    private ProtocolResponse CreateErrorResponse(ProtocolRequest request, string code, string message)
    {
        return new ProtocolResponse
        {
            ProtocolVersion = "1.0",
            RequestId = request.RequestId,
            Success = false,
            Error = new ErrorInfo { Code = code, Message = message }
        };
    }

    private void SendError(string code, string message)
    {
        var response = new ProtocolResponse
        {
            ProtocolVersion = "1.0",
            RequestId = "error",
            Success = false,
            Error = new ErrorInfo { Code = code, Message = message }
        };
        SendResponse(response);
    }

    private void SendResponse(ProtocolResponse response)
    {
        var options = new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
        };
        var json = JsonSerializer.Serialize(response, options);
        Console.Out.WriteLine(json);
        Console.Out.Flush();
    }
}

class MsalAuthDelegate : Microsoft.InformationProtection.IAuthDelegate
{
    private readonly string _tenantId;
    private readonly string _clientId;
    private readonly string _clientSecret;
    private readonly int _timeoutSeconds;

    public MsalAuthDelegate(string tenantId, string clientId, string clientSecret, int timeoutSeconds)
    {
        _tenantId = tenantId;
        _clientId = clientId;
        _clientSecret = clientSecret;
        _timeoutSeconds = timeoutSeconds;
    }

    public string AcquireToken(Microsoft.InformationProtection.Identity identity, string authority, string resource, string claimsChallenge)
    {
        var authorityUri = new Uri(authority);
        var tenantAuthority =
            $"{authorityUri.Scheme}://{authorityUri.Host}/{_tenantId}";

        var app = ConfidentialClientApplicationBuilder
            .Create(_clientId)
            .WithClientSecret(_clientSecret)
            .WithAuthority(tenantAuthority)
            .Build();

        DiagnosticLog.Write("before MSAL token acquisition");
        var tokenRequest = app.AcquireTokenForClient(new[] { $"{resource}/.default" });
        if (!string.IsNullOrWhiteSpace(claimsChallenge))
            tokenRequest = tokenRequest.WithClaims(claimsChallenge);

        using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(_timeoutSeconds));
        var result = tokenRequest.ExecuteAsync(cancellation.Token).GetAwaiter().GetResult();
        DiagnosticLog.Write("after MSAL token acquisition");
        return result.AccessToken;
    }
}

class ConsentDelegate : Microsoft.InformationProtection.IConsentDelegate
{
    public Microsoft.InformationProtection.Consent GetUserConsent(string url)
    {
        return Microsoft.InformationProtection.Consent.Accept;
    }
}

class MipLogger : Microsoft.InformationProtection.ILoggerDelegate
{
    public void Init(string storagePath) { }
    public void Flush() { }
    public void WriteToLog(Microsoft.InformationProtection.LogLevel level, string message, string source, string context, int stackTraceDepth)
    {
        if (level == Microsoft.InformationProtection.LogLevel.Error)
            Console.Error.WriteLine($"[MIP] {message}");
    }
}

class ProtocolRequest
{
    [JsonPropertyName("protocol_version")]
    public string? ProtocolVersion { get; set; }

    [JsonPropertyName("request_id")]
    public string RequestId { get; set; } = "";

    [JsonPropertyName("command")]
    public string Command { get; set; } = "";

    [JsonPropertyName("tenant_id")]
    public string? TenantId { get; set; }

    [JsonPropertyName("client_id")]
    public string? ClientId { get; set; }

    [JsonPropertyName("certificate_path")]
    public string? CertificatePath { get; set; }

    [JsonPropertyName("authorization_mode")]
    public string? AuthorizationMode { get; set; }

    [JsonPropertyName("delegated_user")]
    public string? DelegatedUser { get; set; }

    [JsonPropertyName("source_path")]
    public string? SourcePath { get; set; }

    [JsonPropertyName("output_path")]
    public string? OutputPath { get; set; }

    [JsonPropertyName("timeout_seconds")]
    public int TimeoutSeconds { get; set; } = 120;

    [JsonPropertyName("client_secret")]
    public string? ClientSecret { get; set; }
}

class ProtocolResponse
{
    [JsonPropertyName("protocol_version")]
    public string ProtocolVersion { get; set; } = "1.0";

    [JsonPropertyName("request_id")]
    public string RequestId { get; set; } = "";

    [JsonPropertyName("success")]
    public bool Success { get; set; }

    [JsonPropertyName("result")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public object? Result { get; set; }

    [JsonPropertyName("error")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public ErrorInfo? Error { get; set; }
}

class ErrorInfo
{
    [JsonPropertyName("code")]
    public string Code { get; set; } = "";

    [JsonPropertyName("message")]
    public string Message { get; set; } = "";
}

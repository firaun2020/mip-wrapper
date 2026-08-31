using System;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

class Program
{
    static void Main()
    {
        var helper = new Helper();
        helper.Run();
    }
}

class Helper
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

                // Validate protocol version
                if (request.ProtocolVersion != "1.0")
                {
                    SendError("UnsupportedProtocolVersion", $"Protocol version {request.ProtocolVersion} not supported");
                    continue;
                }

                // Route to command handler
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
        // Placeholder: Would connect to MIP SDK here
        // For now, return mock protected file metadata

        if (string.IsNullOrEmpty(request.SourcePath))
            return CreateErrorResponse(request, "ConfigurationError", "source_path is required");

        var fileInfo = new
        {
            is_protected = true,
            label_id = "12345678-1234-1234-1234-123456789012",
            tenant_id = request.TenantId,
            file_format = Path.GetExtension(request.SourcePath).TrimStart('.'),
            protection_type = "azure_rms",
            usage_rights = new[] { "Edit", "Export", "Print" },
            can_decrypt = true,
            sdk_version = "1.18.124",
            helper_version = "1.0.0"
        };

        return CreateSuccessResponse(request, fileInfo);
    }

    private ProtocolResponse HandleDecrypt(ProtocolRequest request)
    {
        // Placeholder: Would use MIP SDK to decrypt
        // For now, copy source to output (simulates decryption)

        if (string.IsNullOrEmpty(request.SourcePath))
            return CreateErrorResponse(request, "ConfigurationError", "source_path is required");

        if (string.IsNullOrEmpty(request.OutputPath))
            return CreateErrorResponse(request, "ConfigurationError", "output_path is required");

        try
        {
            // Check that source exists
            if (!File.Exists(request.SourcePath))
                return CreateErrorResponse(request, "FileNotFound", $"Source file not found: {request.SourcePath}");

            // Copy source to output (placeholder for actual decryption)
            File.Copy(request.SourcePath, request.OutputPath, overwrite: true);
            var fileInfo = new FileInfo(request.OutputPath);

            var result = new
            {
                output_path = request.OutputPath,
                size_bytes = fileInfo.Length,
                file_format = fileInfo.Extension.TrimStart('.')
            };

            return CreateSuccessResponse(request, result);
        }
        catch (Exception ex)
        {
            return CreateErrorResponse(request, "DecryptionError", ex.Message);
        }
    }

    private ProtocolResponse HandleShutdown(ProtocolRequest request)
    {
        return CreateSuccessResponse(request, new { });
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
    public int TimeoutSeconds { get; set; } = 30;
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

    [JsonPropertyName("details")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Details { get; set; }
}

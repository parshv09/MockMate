/**
 * Extracts user-friendly error messages and DRF field-level validation errors
 * from Axios error responses.
 */
export function extractApiError(error, fallbackMessage = "Something went wrong. Please try again.") {
  if (!error) {
    return {
      message: fallbackMessage,
      fieldErrors: {},
      isNetworkError: false,
      status: null,
    };
  }

  // Network / backend unreachable (no HTTP response received)
  if (!error.response) {
    return {
      message: "Unable to reach the MockMate server. Please check your connection and try again.",
      fieldErrors: {},
      isNetworkError: true,
      status: null,
    };
  }

  const { status, data } = error.response;
  const fieldErrors = {};
  let message = fallbackMessage;

  if (typeof data === "string" && data.trim()) {
    message = data.trim();
  } else if (data && typeof data === "object") {
    if (typeof data.detail === "string" && data.detail.trim()) {
      message = data.detail.trim();
    } else if (Array.isArray(data.non_field_errors) && data.non_field_errors.length > 0) {
      message = String(data.non_field_errors[0]);
    } else if (typeof data.message === "string" && data.message.trim()) {
      message = data.message.trim();
    }

    for (const [key, value] of Object.entries(data)) {
      if (key === "detail" || key === "non_field_errors" || key === "message") {
        continue;
      }
      if (Array.isArray(value) && value.length > 0) {
        fieldErrors[key] = String(value[0]);
      } else if (typeof value === "string" && value.trim()) {
        fieldErrors[key] = value.trim();
      }
    }

    // If no top-level message was found but field errors exist, surface a clear summary
    const firstFieldMessage = Object.values(fieldErrors)[0];
    if (message === fallbackMessage && firstFieldMessage) {
      message = firstFieldMessage;
    }
  }

  if (status >= 500 && message === fallbackMessage) {
    message = "The server encountered an unexpected error. Please try again shortly.";
  }

  return {
    message,
    fieldErrors,
    isNetworkError: false,
    status,
  };
}


// IMPORTANT: Make sure to add GOOGLE_DRIVE_SECURE_TOKEN in Script Properties with the value from your .env file

// Utility functions
function sanitizeFolderName(name) {
  // First normalize accented characters
  const normalized = name.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  // Then replace any remaining invalid characters with underscore
  return normalized.replace(/[^a-z0-9]/gi, '_');
}

function verifyToken(token) {
  var scriptProperties = PropertiesService.getScriptProperties();
  var validToken = scriptProperties.getProperty('GOOGLE_DRIVE_SECURE_TOKEN');
  return token === validToken;
}

// Function to create a nested folder inside a parent folder
function createNestedFolder(parentFolderId, folderName) {
  try {
    var parentFolder = DriveApp.getFolderById(parentFolderId);
    var sanitizedName = sanitizeFolderName(folderName);
    
    // Check if folder already exists
    var existingFolders = parentFolder.getFoldersByName(sanitizedName);
    if (existingFolders.hasNext()) {
      var existingFolder = existingFolders.next();
      return {
        success: true,
        folderId: existingFolder.getId(),
        message: 'Folder already exists'
      };
    }
    
    var newFolder = parentFolder.createFolder(sanitizedName);
    return {
      success: true,
      folderId: newFolder.getId(),
      message: 'Folder created successfully'
    };
  } catch (error) {
    return {
      success: false,
      message: 'Error creating folder: ' + error.toString()
    };
  }
}

// Function to upload a file to a specific folder
function uploadFile(folderId, fileName, fileData, mimeType) {
  try {
    var folder = DriveApp.getFolderById(folderId);
    var blob = Utilities.newBlob(Utilities.base64Decode(fileData), mimeType, fileName);
    var file = folder.createFile(blob);
    
    return {
      success: true,
      fileId: file.getId(),
      message: 'File uploaded successfully'
    };
  } catch (error) {
    return {
      success: false,
      message: 'Error uploading file: ' + error.toString()
    };
  }
}

// Function to delete a file from Drive
function deleteFile(fileId) {
  try {
    var file = DriveApp.getFileById(fileId);
    file.setTrashed(true);
    return {
      success: true,
      message: 'File deleted successfully'
    };
  } catch (error) {
    return {
      success: false,
      message: 'Error deleting file: ' + error.toString()
    };
  }
}

// Function to delete a folder from Drive
function deleteFolder(folderId) {
  try {
    var folder = DriveApp.getFolderById(folderId);
    folder.setTrashed(true);
    return {
      success: true,
      message: 'Folder deleted successfully'
    };
  } catch (error) {
    return {
      success: false,
      message: 'Error deleting folder: ' + error.toString()
    };
  }
}

// Function to overwrite an existing file
function overwriteFile(fileId, fileData, mimeType) {
  try {
    var file = DriveApp.getFileById(fileId);
    var blob = Utilities.newBlob(Utilities.base64Decode(fileData), mimeType);
    file.setContent(blob);
    
    return {
      success: true,
      message: 'File overwritten successfully'
    };
  } catch (error) {
    return {
      success: false,
      message: 'Error overwriting file: ' + error.toString()
    };
  }
}

// Function to rename a folder in Drive
function renameFolder(folderId, newName) {
  try {
    var folder = DriveApp.getFolderById(folderId);
    var sanitizedName = sanitizeFolderName(newName);
    folder.setName(sanitizedName);
    
    return {
      success: true,
      message: 'Folder renamed successfully'
    };
  } catch (error) {
    return {
      success: false,
      message: 'Error renaming folder: ' + error.toString()
    };
  }
}

// Function to get file content
function getFileContent(fileId) {
  try {
    var file = DriveApp.getFileById(fileId);
    var blob = file.getBlob();
    var content = Utilities.base64Encode(blob.getBytes());
    
    return {
      success: true,
      content: content,
      mimeType: blob.getContentType(),
      fileName: file.getName()
    };
  } catch (error) {
    return {
      success: false,
      message: 'Error getting file content: ' + error.toString()
    };
  }
}

// Function to copy a Google Doc template and replace placeholders
function copyDocumentFromTemplate(templateId, newFileName, placeholders, folderId) {
  try {
    // Copy the template document
    var templateDoc = DriveApp.getFileById(templateId);
    var copiedDoc = templateDoc.makeCopy(newFileName);
    
    // Move to the specified folder if provided
    if (folderId) {
      var folder = DriveApp.getFolderById(folderId);
      copiedDoc.getParents().next().removeFile(copiedDoc);
      folder.addFile(copiedDoc);
    }
    
    // Open the copied document and replace placeholders
    var doc = DocumentApp.openById(copiedDoc.getId());
    var body = doc.getBody();
    
    // Replace placeholders in the document
    for (var placeholder in placeholders) {
      if (placeholders.hasOwnProperty(placeholder)) {
        body.replaceText(placeholder, placeholders[placeholder]);
      }
    }
    
    // Save and close the document
    doc.saveAndClose();
    
    return {
      success: true,
      fileId: copiedDoc.getId(),
      fileName: newFileName,
      fileUrl: 'https://docs.google.com/document/d/' + copiedDoc.getId(),
      message: 'Document created successfully from template'
    };
  } catch (error) {
    return {
      success: false,
      message: 'Error creating document from template: ' + error.toString()
    };
  }
}

// Function to update an existing Google Doc with new placeholders
function updateDocumentPlaceholders(documentId, placeholders) {
  try {
    var doc = DocumentApp.openById(documentId);
    var body = doc.getBody();
    
    // Replace placeholders in the document
    for (var placeholder in placeholders) {
      if (placeholders.hasOwnProperty(placeholder)) {
        body.replaceText(placeholder, placeholders[placeholder]);
      }
    }
    
    // Save and close the document
    doc.saveAndClose();
    
    return {
      success: true,
      message: 'Document updated successfully'
    };
  } catch (error) {
    return {
      success: false,
      message: 'Error updating document: ' + error.toString()
    };
  }
}

// Function to handle HTTP requests
function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    
    // Verify token
    if (!verifyToken(data.token)) {
      return ContentService
        .createTextOutput(JSON.stringify(createErrorResponse('Invalid token')))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    var action = data.action;
    var result;
    
    switch (action) {
      case 'createNestedFolder':
        result = handleCreateNestedFolder(data);
        break;
      case 'uploadFile':
        result = handleUploadFile(data);
        break;
      case 'deleteFile':
        result = handleDeleteFile(data);
        break;
      case 'deleteFolder':
        result = handleDeleteFolder(data);
        break;
      case 'overwriteFile':
        result = handleOverwriteFile(data);
        break;
      case 'renameFolder':
        result = handleRenameFolder(data);
        break;
      case 'getFileContent':
        result = handleGetFileContent(data);
        break;
      case 'copyDocumentFromTemplate':
        result = handleCopyDocumentFromTemplate(data);
        break;
      case 'updateDocumentPlaceholders':
        result = handleUpdateDocumentPlaceholders(data);
        break;
      default:
        result = createErrorResponse('Unknown action: ' + action);
        break;
    }
    
    return ContentService
      .createTextOutput(JSON.stringify(result))
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify(createErrorResponse('Server error: ' + error.toString())))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// Response creators
function createSuccessResponse(data) {
  return {
    success: true,
    ...data
  };
}

function createErrorResponse(message) {
  return {
    success: false,
    message: message
  };
}

// Action handlers
function handleCreateNestedFolder(data) {
  if (!data.parentFolderId || !data.folderName) {
    return createErrorResponse('Missing required fields: parentFolderId, folderName');
  }
  
  var result = createNestedFolder(data.parentFolderId, data.folderName);
  return result;
}

function handleUploadFile(data) {
  if (!data.folderId || !data.fileName || !data.fileData || !data.mimeType) {
    return createErrorResponse('Missing required fields: folderId, fileName, fileData, mimeType');
  }
  
  var result = uploadFile(data.folderId, data.fileName, data.fileData, data.mimeType);
  return result;
}

function handleDeleteFile(data) {
  if (!data.fileId) {
    return createErrorResponse('Missing required field: fileId');
  }
  
  var result = deleteFile(data.fileId);
  return result;
}

function handleDeleteFolder(data) {
  if (!data.folderId) {
    return createErrorResponse('Missing required field: folderId');
  }
  
  var result = deleteFolder(data.folderId);
  return result;
}

function handleOverwriteFile(data) {
  if (!data.fileId || !data.fileData || !data.mimeType) {
    return createErrorResponse('Missing required fields: fileId, fileData, mimeType');
  }
  
  var result = overwriteFile(data.fileId, data.fileData, data.mimeType);
  return result;
}

function handleRenameFolder(data) {
  if (!data.folderId || !data.newName) {
    return createErrorResponse('Missing required fields: folderId, newName');
  }
  
  var result = renameFolder(data.folderId, data.newName);
  return result;
}

function handleGetFileContent(data) {
  if (!data.fileId) {
    return createErrorResponse('Missing required field: fileId');
  }
  
  var result = getFileContent(data.fileId);
  return result;
}

function handleCopyDocumentFromTemplate(data) {
  if (!data.templateId || !data.newFileName || !data.placeholders) {
    return createErrorResponse('Missing required fields: templateId, newFileName, placeholders');
  }
  
  var result = copyDocumentFromTemplate(data.templateId, data.newFileName, data.placeholders, data.folderId);
  return result;
}

function handleUpdateDocumentPlaceholders(data) {
  if (!data.documentId || !data.placeholders) {
    return createErrorResponse('Missing required fields: documentId, placeholders');
  }
  
  var result = updateDocumentPlaceholders(data.documentId, data.placeholders);
  return result;
}

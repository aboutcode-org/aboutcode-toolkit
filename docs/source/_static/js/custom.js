$(document).ready(function () {
    $('a[href^="file://"], a[href^="http://"], a[href^="https://"]').not('a[class*=internal]').attr('target', '_blank');
    $('a[href$=".docx"], a[href$=".xlsx"]').not('a[class*=internal]').attr('target', '_self');
 });

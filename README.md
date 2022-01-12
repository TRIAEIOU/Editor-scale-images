# Editor scale images

Editor scale images (ESI) is a minimal pure JS (i.e. no jquery etc.) implementation to allow scaling images in the Anki Desktop editor _maintaing aspect ratio only_ (design choice).

**\*\*\*\* All credit for concept to Arthur Milchior (https://github.com/Arthur-Milchior/) and his excellent addon "Resize images in editor" (https://ankiweb.net/shared/info/1103084694) however all code written from scratch \*\*\*\***

Arthur Milchiors addon is much more configurable, ESI aims to be as simple as possible:
- Keep the code as simple as possible and reduce the number of event listeners registered and js execution for complex notes with many images to reduce Anki editor lag.
- Ensure aspect ratio is preserved, even inside tables, during reviewing.
- Leave as much of the img-tag untouched as possible (addon will change the following properties of the img inline style: display, pointer-events, object-fit, height, width, min-width, max-width).
- Simplify moving/copying/pasting of img in the editor by leaving img tags "untouched" unless they are selected (and automatically deselecting them as soon as the user does something other than resize inside the editor field, i.e. scrolling etc. will not deselect the img).

## Use
1. Click on the image to resize, it will become "selected" (surrounded by a dashed border).
2. Resize by dragging the lower right corner (cursor will be crosshair over image but arrow over the dragging corner).
3. Continue to edit the note (img will be deselected as soon as you start typing or click somewhere else, no need to actively deselect and remember "Escape" will close the Add note/Browser window).

## Configuration
- Set the highlight border style in the addon configuration (CSS "border" property, eg. `5px solid red` will result in a solid red border, 5px wide). Default: `1px solid black`.

## Remarks
- There is little visible indication apart from the cursor type of where the draggable corner is located to reduce the number of inserted elements (otherwise an additional overlay img or div could be inserted over the draggable corner to indicate it's location).
- ESI will be incompatible with any addon that depends on/changes any of the following style properties: display, pointer-events, object-fit, height, width, min-width, max-width. Changing any other style properties or img attributes should be OK (assuming the rendering engine gives prescedence to inline style height/width/min-width/max-width). This is a design choice, so addon incompatibilty due to this will not be addressed.
- ESI will be incompatible with any addon using similar concepts for image resize or wrapping img tags in divs.
- The note "source" is kept intact until an img is selected, then that img alone is wrapped in a scalable div for resizing. Once deselected (on click outside img or any keypress) the div is removed (and inline style properties set appropriately). Any selected ("div-wrapped") are "unwrapped" before note save to database keeping the database clean.
- Anki 2.1.50 (or more specifically Qt6 QWebEngine) will give some more implementation options as the Qt6 QWebEngine should implement the CSS aspect-ratio property (not implemented in Qt5 QWebEngine).
- Untested on MacOS/iOS Anki due to lack of testing platforms but it should be OK as ESI doesn't use any edge case HTML/JS functionality.

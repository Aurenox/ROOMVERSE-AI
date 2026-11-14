# Spot-the-change artwork

Built-in image generation edited `frontend/public/art/midnight-original.png` into two sibling assets, preserving the original file:

- `frontend/public/art/midnight-change-a.png`: desk lamp removed.
- `frontend/public/art/midnight-change-b.png`: rear globe and stand removed.

Prompt used for each variant: Edit this exact detective office scene for a visual memory spot-the-change game. Remove ONLY [the entire brass desk lamp on the right side of the desk, including its shade, arm, and base / the globe and its stand on the cabinet at the rear left of the room]. Fill the newly exposed area naturally with the underlying desk or cabinet and wall. Preserve every other object, all papers, chair, glasses, plants, camera, background, composition, framing, perspective and colors. Preserve the original lighting as much as possible even when removing the lamp. Do not move or remove any other object. Same image dimensions and framing as input. No text, markers, arrows or new objects. The ONLY meaningful change must be that the specified object is missing.

Both outputs were visually inspected against the original. Answer options describe object presence, not minor lighting/rendering differences. The two edited images are finite. Each is issued at most twice per owner across saved attempt history, with at most one missing-object round in a case. Once consumed, the case uses fresh witness-caption associations instead of repeating these images. Guest tracking depends on retaining the session cookie; an account carries history across devices.

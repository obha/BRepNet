const Command = require("../Command.js");
import { SetPositionCommand } from "./SetPositionCommand.js";
import { SetRotationCommand } from "./SetRotationCommand.js";
import { SetScaleCommand } from "./SetScaleCommand.js";
import { AddObjectCommand } from "./AddObjectCommand.js";

class UpdateObjectCommand extends Command {
  /**
   * @param {import('../Editor.js').Editor} editor
   * @param {THREE.Object3D} object
   * @constructor
   */
  constructor(editor, object) {
    super(editor);

    this.type = "UpdateObjectCommand";
    this.updatable = true;

    if (object !== undefined) {
      this.name = `Update Object: ${object.name}`;

      if (!editor.objectByUuid(object.uuid)) {
        editor.execute(new AddObjectCommand(editor, object));
      }

      this.positionCmd = new SetPositionCommand(
        editor,
        object,
        object.position
      );
      this.rotationCmd = new SetRotationCommand(
        editor,
        object,
        object.rotation
      );
      this.scaleCmd = new SetScaleCommand(editor, object, object.scale);
    }
  }

  execute() {
    this.positionCmd.execute();
    this.rotationCmd.execute();
    this.scaleCmd.execute();
  }

  undo() {
    this.positionCmd.undo();
    this.rotationCmd.undo();
    this.scaleCmd.undo();
  }

  update(command) {}

  toJSON() {
    const output = super.toJSON(this);

    output.object = this.object.toJSON();

    return output;
  }

  fromJSON(json) {
    super.fromJSON(json);

    this.object = this.editor.objectByUuid(json.object.object.uuid);

    if (this.object === undefined) {
      const loader = new THREE.ObjectLoader();
      this.object = loader.parse(json.object);
    }
  }
}

export { UpdateObjectCommand };

/**
 * @param editor pointer to main editor object used to initialize
 *        each command object with a reference to the editor
 * @constructor
 */

class Command {
	setUpdatable(value = true) {
		this.updatable = value;

		return this;
	}

	/**
	 * @param {import('../Editor.js').Editor} editor
	 * @constructor
	 */
	constructor(editor) {
		this.id = -1;
		this.inMemory = false;
		this.updatable = false;
		this.type = '';
		this.name = '';
		this.editor = editor;
	}

	execute() {}

	/**
	 *
	 * @param {Command} command
	 */
	update(command) {}

	toJSON() {
		const output = {};
		output.type = this.type;
		output.id = this.id;
		output.name = this.name;
		return output;
	}

	fromJSON(json) {
		this.inMemory = true;
		this.type = json.type;
		this.id = json.id;
		this.name = json.name;
	}
}

export { Command };

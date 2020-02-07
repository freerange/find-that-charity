import React from 'react'

import { set_fields_to_add } from "../../../actions/Actions"

export const potentialFieldsToAdd = [
    { slug: 'postcode', name: 'Postcode' },
    { slug: 'latest_income', name: 'Latest income' },
    { slug: 'known_as', name: 'Name' },
]

class FieldsToAdd extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            loaded: false,
            potentialFieldsToAdd: potentialFieldsToAdd
        }
        this.handleChange = this.handleChange.bind(this);
        this.selectAllFields = this.selectAllFields.bind(this);
    }

    componentDidMount() {
        this.setState({ loaded: false });
        let properties_url = `/reconcile/propose_properties`

        fetch(properties_url)
            .then(function (response) {
                return response.json();
            })
            .then(result => this.setState({
                potentialFieldsToAdd: result.properties,
                loaded: true
            }))
            .catch(error => this.setState({
                error,
                loaded: true
            }));
    }

    handleChange(event) {
        let fieldsToAdd = this.props.fieldsToAdd;
        if (event.target.checked) {
            if (!fieldsToAdd.includes(event.target.value)) {
                fieldsToAdd = fieldsToAdd.concat([event.target.value]);
            }
        } else {
            fieldsToAdd = fieldsToAdd.filter(e => e !== event.target.value);
        }
        this.props.dispatch(set_fields_to_add(fieldsToAdd));
    }

    selectAllFields() {
        this.props.dispatch(set_fields_to_add(this.state.potentialFieldsToAdd.map((f) => f.id)));
    }

    render() {
        return (
            <div className="field">
                <label className="label">Select fields to add</label>
                <a onClick={this.selectAllFields} style={{ cursor: 'pointer' }}>Select all fields</a>
                <div className="control">
                    {this.state.loaded && this.state.potentialFieldsToAdd.map((field, i) =>
                        <div key={i}>
                            <label className="checkbox">
                                <input type="checkbox" 
                                    value={field.id} 
                                    checked={this.props.fieldsToAdd.includes(field.id)}
                                    onChange={this.handleChange} /> {field.name}
                            </label>
                        </div>
                    )}
                </div>
            </div>
        )
    }
}

export default FieldsToAdd;
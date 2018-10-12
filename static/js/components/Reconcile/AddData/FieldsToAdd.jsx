import React from 'react'

import { set_fields_to_add } from "../../../actions/Actions"

export const defaultPotentialFieldsToAdd = [
    { id: 'postalCode', name: 'Postcode' },
    { id: 'latestIncome', name: 'Latest income' },
    { id: 'name', name: 'Name' },
]

class FieldsToAdd extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            isLoaded: false,
            potentialFieldsToAdd: []
        }
        this.handleChange = this.handleChange.bind(this);
    }

    componentDidMount() {
        fetch("/propose_properties")
          .then(res => res.json())
          .then(result => {
              this.setState({
                  potentialFieldsToAdd: result.properties,
                  isLoaded: true
              });
            },
            // Note: it's important to handle errors here
            // instead of a catch() block so that we don't swallow
            // exceptions from actual bugs in components.
            error => {
                this.setState({
                    isLoaded: true,
                    potentialFieldsToAdd: defaultPotentialFieldsToAdd
                });
            });
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

    render() {
        if(!this.state.isLoaded) {
            return <div>Loading...</div>;
        } else {
            return (
                <div className="field">
                    <label className="label">Select fields to add</label>
                    <div className="control">
                        {this.state.potentialFieldsToAdd.map((field, i) =>
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
}

export default FieldsToAdd;
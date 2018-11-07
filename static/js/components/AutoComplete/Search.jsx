import React from "react";

export default class SearchAutoComplete extends React.Component {
    constructor(props) {
        super(props);
        this.state = { results: [], loading: false, q: props.value, orgtype: props.selected_org_type };
        this.handleChange = this.handleChange.bind(this);
    }

    handleChange(e) {
        this.setState({
            [e.target.name]: e.target.value,
            "results": []
        });
    }

    componentDidUpdate(){
        if (this.state.q.length > 2) {
            if(this.state.results.length==0) {
                if (this.state.loading == false) {
                    this.setState({ "loading": true });
                } else {
                    this._fetchAutocomplete(this.state.q, this.state.orgtype)
                }
            }
        }
        return true;
    }

    _fetchAutocomplete(q, orgtype) {
        var element = this;
        fetch(`/autocomplete?q=${encodeURIComponent(q)}&orgtype=${encodeURIComponent(orgtype)}`)
            .then(function (response) {
                return response.json();
            })
            .then(function (resultJson) {
                element.setState({
                    "results": resultJson["results"],
                    "loading": false
                });
            });
    }

    getHighlightedText(text, highlight) {
        // Split text on higlight term, include term itself into parts, ignore case
        // https://stackoverflow.com/questions/29652862/highlight-text-using-reactjs
        if(!highlight){
            return <span>{text}</span>
        }
        var parts = text.split(new RegExp(`(${highlight})`, 'gi'));
        return <span>{parts.map((part, i) => part.toLowerCase() === highlight.toLowerCase() ? <b key={i}>{part}</b> : part)}</span>;
    }

    render() {
        return (
            <div className="dropdown is-active" style={{ display: 'block', width: '100%' }}>
                <div className="dropdown-trigger field has-addons has-addons-centered">
                    <div className={(this.state.loading ? "is-loading" : "") + " control is-expanded"}>
                        <input value={this.state.q}
                            onChange={this.handleChange}
                            name="q"
                            className="input is-large is-fullwidth"
                            placeholder="Search for a charity name or number"
                            type="text"
                            aria-haspopup="true"
                            aria-controls="dropdown-menu"
                            autoComplete="off" />
                    </div>
                    <div className="control">
                        <span className="select is-large">
                            <select value={this.state.orgtype}
                                onChange={this.handleChange}
                                name="orgtype">
                                <option value="all">All organisation types</option>
                                <option readOnly>----------</option>
                                {Object.keys(this.props.org_types).map((org_type, i) => 
                                    <option key={i}>{org_type}</option>    
                                )}
                            </select>
                        </span>
                    </div>
                    <div className="control">
                        <input type="submit" value="Search" className="button is-info is-large" />
                    </div>
                </div>
                {this.state.results.length > 0 &&
                    <div className="dropdown-menu" id="dropdown-menu" role="menu" style={{ width: '100%' }}>
                        <div className="dropdown-content">
                            {this.state.results.map((result, i) =>
                                <React.Fragment key={i}>
                                    {i > 0 && <hr className="dropdown-divider" />}
                                    <a href={"/orgid/" + result.value} data-value={result.value} data-label={result.label} className="dropdown-item">
                                        <div className="columns">
                                            <div className="column">
                                                {this.getHighlightedText(result.label, this.state.q)}
                                                {result.orgtypes.map((orgtype, i) =>
                                                <span key={i} className="tag" style={{marginLeft: '5px'}}>{orgtype}</span>
                                                )}
                                            </div>
                                            <div className="column is-italic has-text-grey is-narrow">{result.value}</div>
                                        </div>
                                    </a>
                                </React.Fragment>
                            )}
                        </div>
                    </div>
                }
            </div>
        )
    }
}
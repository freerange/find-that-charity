const DEFAULT_HASH_LENGTH = 4;
var current_stage = 'select-file';

var stages = [
    'select-file',
    'select-orgid-field',
    'select-fields'
];

function hide_stage(stage, show_top) {
    var stage_el = document.getElementById('stage-' + stage);
    Array.from(stage_el.getElementsByClassName('contents'))
        .forEach(i => i.classList.add("dn"));
    if (show_top) {
        Array.from(stage_el.getElementsByClassName('contents-top'))
            .forEach(i => i.classList.remove("dn"));
    } else {
        Array.from(stage_el.getElementsByClassName('contents-top'))
            .forEach(i => i.classList.add("dn"));
    }
}

function show_stage(stage) {
    var stage_el = document.getElementById('stage-' + stage);
    Array.from(stage_el.getElementsByClassName('contents'))
        .forEach(i => i.classList.remove("dn"));
    Array.from(stage_el.getElementsByClassName('contents-top'))
        .forEach(i => i.classList.add("dn"));
}

function set_stage(stage) {
    current_stage = stage;
    var previous_stages = stages.slice(0, stages.indexOf(stage));
    var next_stages = stages.slice(stages.indexOf(stage) + 1);

    previous_stages.forEach(s => hide_stage(s, true));
    next_stages.forEach(s => hide_stage(s, false));
    show_stage(stage);
}

function clean_orgid(pc) {
    if (typeof pc === 'string' || pc instanceof String) {
        pc = pc.toUpperCase().replace(/[^A-Z0-9]/, '');
        return pc.slice(0, -3) + " " + pc.slice(-3);
    }
    return pc;
}

function hash_orgid(pc, length) {
    length = length || DEFAULT_HASH_LENGTH;
    pc = pc.toLowerCase().replace(/[^a-z0-9]/, '');
    var pchash = CryptoJS.MD5(pc);
    return pchash.toString(CryptoJS.enc.Hex).slice(0, length);
}

function update_fields_list(results, div) {
    div.innerHTML = '';
    var ul = document.createElement('ul');
    ul.classList.add('list', 'pa0', 'ma0');
    for (const f of results.meta.fields) {
        var f_slug = f.toLowerCase().replace(/"\s+"/gi, "-").replace(/[^a-z0-9]/gi, '');
        var li = document.createElement('li');
        li.classList.add('mb2');
        var label = document.createElement('label');
        label.setAttribute('for', "field-" + f_slug);
        label.classList.add('pointer');
        var span = document.createElement('span');
        span.innerText = f;
        span.classList.add('code', 'pa1', 'bg-light-gray', 'underline-hover');
        var radio = document.createElement('input');
        radio.setAttribute('type', 'radio');
        radio.setAttribute('name', 'orgid_field');
        radio.setAttribute('value', f);
        radio.setAttribute('id', "field-" + f_slug);
        radio.classList.add('dn');

        if (f_slug.includes("charitynumber") | f_slug.includes("recipientorgid") | 
            f_slug.includes("orgid") | f_slug.includes("organisationidentifier")) {
            radio.setAttribute('checked', true);
            document.getElementById('column_name').setAttribute('value', f);
            document.getElementById('column-name-desc').innerText = f + " (autodetected)";
        }
        radio.onclick = function () {
            if (this.checked) {
                document.getElementById('column_name').setAttribute('value', this.value);
                document.getElementById('column-name-desc').innerText = f;
                set_stage('select-fields');
            }
        }

        var field_ul = document.createElement('ul');
        field_ul.classList.add('list', 'pa0', 'ma0');
        let values_seen = []
        for (const r of results.data) {
            if ((!values_seen.includes(r[f])) && (r[f] != '') && (typeof r[f] != 'undefined')) {
                var field_li = field_ul.appendChild(document.createElement('li'))
                field_li.classList.add('dib', 'mr2', 'gray', 'mt1', 'f6', 'tl', 'truncate', 'mw5');
                field_li.appendChild(document.createTextNode('"' + r[f] + '"'));
                values_seen.push(r[f]);
            }
            if (values_seen.length >= 5) {
                break;
            }
        }

        label.append(radio);
        label.append(span);
        label.append(field_ul);
        li.append(label);
        ul.appendChild(li);
    }
    div.append(ul);
}

function get_results(hashes, fields_to_add) {
    const url_parameters = new URLSearchParams(fields_to_add.map(f => ['properties', f]));
    var urls = Array.from(hashes.values()).map(hash => {
        var url = new URL(hash_url.replace('xxx', hash));
        url.search = url_parameters.toString();
        return url;
    });
    var rows_done = 0;
    return Promise.all(urls.map(url =>
        fetch(url)
            .then(res => res.json())
            .then((data) => {
                rows_done++;
                var percent_done = ((rows_done / urls.length) * 100).toFixed(1) + "%"
                document.getElementById("result-text").innerText = "Creating file…";
                document.getElementById("progress-bar-inner").innerText = percent_done;
                document.getElementById("progress-bar-inner").style.width = percent_done;
                return Object.fromEntries(
                    data.data.map(i => [
                        i["id"],
                        Object.fromEntries(
                            Object.entries(i).filter(v => v[0] != "id")
                        )
                    ])
                );
            })
            .catch((error) => {
                console.log('Error: ', error)
            })
    ))
        .then(data => Object.assign({}, ...data))
}

function parse_fields_to_add(fields) {

    if (fields.includes("latlng")) {
        fields.splice(fields.indexOf("latlng"), 1, "lat", "long");
    }

    if (fields.includes("estnrth")) {
        fields.splice(fields.indexOf("estnrth"), 1, "oseast1m", "osnrth1m");
    }

    if (fields.includes("lep")) {
        fields.splice(fields.indexOf("lep"), 1, "lep1", "lep2");
    }

    if (fields.includes("lep_name")) {
        fields.splice(fields.indexOf("lep_name"), 1, "lep1_name", "lep2_name");
    }
    return fields;
}

function openSaveFileDialog(data, filename, mimetype) {
    // from: https://github.com/mholt/PapaParse/issues/175#issuecomment-395978144

    if (!data) return;

    var blob = data.constructor !== Blob
        ? new Blob([data], { type: mimetype || 'application/octet-stream' })
        : data;

    if (navigator.msSaveBlob) {
        navigator.msSaveBlob(blob, filename);
        return;
    }

    var lnk = document.createElement('a'),
        url = window.URL,
        objectURL;

    if (mimetype) {
        lnk.type = mimetype;
    }

    lnk.download = filename || 'untitled';
    lnk.href = objectURL = url.createObjectURL(blob);
    lnk.dispatchEvent(new MouseEvent('click'));
    setTimeout(url.revokeObjectURL.bind(url, objectURL));

}

function create_new_file(results, new_data, column_name, fields_to_add) {
    return Papa.unparse({
        fields: results.meta.fields.concat(fields_to_add),
        data: results.data.map(row => Object.assign(
            row,
            new_data[clean_orgid(row[column_name])]
        ))
    });
}

function click_download(results, filename) {
    var column_name = document.getElementById('column_name').value;

    var hashes = new Set(
        Array.from(results.data)
            .filter(r => r[column_name])
            .map(r => hash_orgid(r[column_name])
            )
    );
    var fields_to_add = parse_fields_to_add(
        Array.from(document.getElementsByName("fields"))
            .filter(i => i.checked)
            .map(i => i.value)
    );
    document.getElementById("result").classList.remove("dn");

    get_results(hashes, fields_to_add).then(data => openSaveFileDialog(
        create_new_file(
            results,
            data,
            column_name,
            fields_to_add,
        ),
        filename.replace(".csv", "-geo.csv")
    ));
}

document.addEventListener('DOMContentLoaded', function (event) {
    document.getElementById('reset-select-orgid-field').onclick = function (ev) {
        ev.preventDefault();
        set_stage('select-orgid-field');
    }
    document.getElementById('reset-select-file').onclick = function (ev) {
        ev.preventDefault();
        set_stage('select-file');
    }

    set_stage('select-file');
    var file = document.getElementById("csvfile");
    file.onchange = function () {
        if (file.files.length > 0) {
            document.getElementById('csvfilename').innerHTML = file.files[0].name;
            document.getElementById('csvpreview').classList.remove("dn");
            // document.getElementById('csvpreview').getElementsByTagName('table')[0].innerHTML = '';
            document.getElementById('csvpreview').innerHTML = '';
            Papa.parse(file.files[0], {
                header: true,
                worker: true,
                complete: function (results) {
                    var preview = document.getElementById('csvpreview');
                    // update_fields_table(results, preview.getElementsByTagName('table')[0]);
                    update_fields_list(results, preview);
                    document.getElementById("fetch_orgids").onclick = function (ev) {
                        ev.preventDefault();
                        click_download(results, file.files[0].name);
                    }
                    document.getElementById('csvfilename').innerHTML = file.files[0].name + " (" + results.data.length + " rows)";

                    if (document.getElementById('column_name').value != "") {
                        set_stage('select-fields');
                    } else {
                        set_stage('select-orgid-field');
                    }
                }
            });
        } else {
            document.getElementById('csvfilename').innerHTML = "";
            document.getElementById('csvpreview').classList.add("dn");
        }
    };

    document.getElementById("select_all_codes").onchange = function (ev) {
        Array.prototype.forEach.call(document.getElementsByName("fields"), function (item) {
            if (!item.value.endsWith("_name")) {
                item.checked = ev.target.checked;
            }
        });
    }

    document.getElementById("select_all_names").onchange = function (ev) {
        Array.prototype.forEach.call(document.getElementsByName("fields"), function (item) {
            if (item.value.endsWith("_name")) {
                item.checked = ev.target.checked;
            }
        });
    }
});
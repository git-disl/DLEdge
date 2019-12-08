import React, { Component } from "react";
import Dropzone from "./Dropzone";
import '../css/Upload.css';
import ObjectDetector from './ObjectDetector';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Button from 'react-bootstrap/Button';

class Upload extends Component {
  constructor(props) {
    super(props);
    this.state = {
      uploading: false,
      uploaded: false,
      src: '',
      image: false
    };

  }

  onFilesAdded = (event) => {
    this.setState({ uploading: true });

    let image = false;
    if (event.target.files[0].type === 'image/png' || event.target.files[0].type === 'image/jpeg') {
      image = true;
    }
    var reader = new FileReader();

    //onload will run after video has been loaded
    reader.onload = file => {
      this.setState({
        uploaded: true,
        uploading: false,
        src: file.target.result,
        image: image
      })
    }

    reader.readAsDataURL(event.target.files[0]);

  }

  componentDidMount() {
    fetch("http://localhost:5000/shutdown",{method:'POST'})
        .then(data => {})
  }

  startOver = ()=>{
    fetch("http://localhost:5000/shutdown",{method:'POST'})
        .then(data => {})
    this.setState({
      uploading: false,
      uploaded: false,
      src: ''
    })
  }

  render() {
    if (this.state.uploaded) {
      return <ObjectDetector src={this.state.src} type={this.state.image? "image" : "video"} back={this.startOver}/>;
    } else {
      return (
        <Container>
          <Row>
            <Button variant="link" onClick={this.props.back} className="backButton">
              <i className="fa fa-arrow-circle-left fa-2x" aria-hidden="true"></i>
            </Button>
          </Row>
          <Row className="uploadContainer">
            <h2 className="title">Upload file</h2>
                <Dropzone
                  onFilesAdded={this.onFilesAdded}
                  disabled={this.state.uploading || this.state.uploaded}
                />
          </Row>

        </Container>
      );
    }

  }
}

export default Upload;

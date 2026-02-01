from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pypdf import PdfReader, PdfWriter
from PIL import Image
import io
import tempfile
import os

app = Flask(__name__)
CORS(app)

@app.route('/unlock', methods=['POST'])
def unlock_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    password = request.form.get('password', '')
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_in:
        file.save(temp_in.name)
        temp_in.flush()
        reader = PdfReader(temp_in.name)
        if reader.is_encrypted:
            result = reader.decrypt(password)
            if result == 0:
                os.unlink(temp_in.name)
                return jsonify({'error': 'Wrong password or decryption failed'}), 400
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_out:
            writer.write(temp_out)
            temp_out.flush()
            temp_out.seek(0)
            response = send_file(temp_out.name, as_attachment=True, download_name='unlocked.pdf')
        os.unlink(temp_in.name)
        os.unlink(temp_out.name)

@app.route('/add_pdf_password', methods=['POST'])
def add_pdf_password():
    if 'pdf_file' not in request.files:
        return jsonify({'error': 'No PDF file uploaded'}), 400
    file = request.files['pdf_file']
    password = request.form.get('password', '')

    if not password:
        return jsonify({'error': 'Password is required'}), 400

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_in:
        file.save(temp_in.name)
        temp_in.flush()

        reader = PdfReader(temp_in.name)
        if reader.is_encrypted:
            os.unlink(temp_in.name)
            return jsonify({'error': 'PDF is already encrypted. Unlock first if you want to change password.'}), 400

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(password)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_out:
            writer.write(temp_out)
            temp_out.flush()
            temp_out.seek(0)
            response = send_file(temp_out.name, as_attachment=True, download_name='protected.pdf')
        
        os.unlink(temp_in.name)
        os.unlink(temp_out.name)
        return response



@app.route('/convert_image_to_pdf', methods=['POST'])
def convert_image_to_pdf():
    if 'image' not in request.files:
        return jsonify({'error': 'No image part in the request'}), 400

    file = request.files['image']
    password = request.form.get('password', '')

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        try:
            image = Image.open(file.stream).convert('RGB')
            pdf_buffer = io.BytesIO()
            image.save(pdf_buffer, format='PDF')
            pdf_buffer.seek(0)

            if password:
                reader = PdfReader(pdf_buffer)
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                writer.encrypt(password)
                encrypted_pdf_buffer = io.BytesIO()
                writer.write(encrypted_pdf_buffer)
                encrypted_pdf_buffer.seek(0)
                return send_file(encrypted_pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name='converted_protected.pdf')
            else:
                return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name='converted.pdf')
        except Exception as e:
            return jsonify({'error': f'Error converting image to PDF: {e}'}), 500




@app.route('/compress_file', methods=['POST'])
def compress_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    quality = int(request.form.get('quality', 75)) # Default quality for images

    if not (1 <= quality <= 95):
        return jsonify({'error': 'Quality must be between 1 and 95'}), 400

    file_extension = file.filename.rsplit('.', 1)[1].lower()

    if file_extension in ['jpeg', 'jpg', 'png', 'gif']:
        try:
            image = Image.open(file.stream)
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG', quality=quality)
            img_byte_arr.seek(0)
            return send_file(img_byte_arr, mimetype='image/jpeg', as_attachment=True, download_name=f'compressed_image.{file_extension}')
        except Exception as e:
            return jsonify({'error': f'Error compressing image: {e}'}), 500
    elif file_extension == 'pdf':
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_in:
                file.save(temp_in.name)
                temp_in.flush()

            reader = PdfReader(temp_in.name)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            
            writer.compress_content_streams()

            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_out:
                writer.write(temp_out)
                temp_out.flush()
                temp_out.seek(0)
                response = send_file(temp_out.name, as_attachment=True, download_name='compressed.pdf')
            
            os.unlink(temp_in.name)
            os.unlink(temp_out.name)
            return response
        except Exception as e:
            return jsonify({'error': f'Error compressing PDF: {e}'}), 500
    else:
        return jsonify({'error': 'Unsupported file type for compression'}), 400

@app.route('/')
def home():
    return 'PDF Unlocker Backend is running!'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

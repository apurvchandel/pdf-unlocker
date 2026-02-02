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
    
    temp_in_name = None
    temp_out_name = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_in:
            temp_in_name = temp_in.name
            file.save(temp_in.name)
            temp_in.flush()
            
        reader = PdfReader(temp_in_name)
        if reader.is_encrypted:
            result = reader.decrypt(password)
            if result == 0:
                return jsonify({'error': 'Wrong password or decryption failed'}), 400
        
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_out:
            temp_out_name = temp_out.name
            writer.write(temp_out)
            temp_out.flush()
        
        return send_file(temp_out_name, as_attachment=True, download_name='unlocked.pdf')
    except Exception as e:
        return jsonify({'error': f'Error unlocking PDF: {str(e)}'}), 500
    finally:
        if temp_in_name and os.path.exists(temp_in_name):
            os.unlink(temp_in_name)
        if temp_out_name and os.path.exists(temp_out_name):
            os.unlink(temp_out_name)

@app.route('/add_pdf_password', methods=['POST'])
def add_pdf_password():
    if 'pdf_file' not in request.files:
        return jsonify({'error': 'No PDF file uploaded'}), 400
    file = request.files['pdf_file']
    password = request.form.get('password', '')

    if not password:
        return jsonify({'error': 'Password is required'}), 400

    temp_in_name = None
    temp_out_name = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_in:
            temp_in_name = temp_in.name
            file.save(temp_in.name)
            temp_in.flush()

        reader = PdfReader(temp_in_name)
        if reader.is_encrypted:
            return jsonify({'error': 'PDF is already encrypted. Unlock first if you want to change password.'}), 400

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(password)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_out:
            temp_out_name = temp_out.name
            writer.write(temp_out)
            temp_out.flush()
        
        return send_file(temp_out_name, as_attachment=True, download_name='protected.pdf')
    except Exception as e:
        return jsonify({'error': f'Error adding password to PDF: {str(e)}'}), 500
    finally:
        if temp_in_name and os.path.exists(temp_in_name):
            os.unlink(temp_in_name)
        if temp_out_name and os.path.exists(temp_out_name):
            os.unlink(temp_out_name)



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
            # Read the original file to get its size
            file.stream.seek(0)
            original_data = file.stream.read()
            original_size = len(original_data)
            file.stream.seek(0)
            
            image = Image.open(file.stream)
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG', quality=quality)
            img_byte_arr.seek(0)
            
            # Get compressed size
            compressed_size = len(img_byte_arr.getvalue())
            
            # Calculate compression ratio
            compression_ratio = ((original_size - compressed_size) / original_size * 100) if original_size > 0 else 0
            
            response = send_file(
                img_byte_arr,
                mimetype='image/jpeg',
                as_attachment=True,
                download_name=f'compressed_image.{file_extension}'
            )
            
            # Add custom headers with file size information
            response.headers['X-Original-Size'] = str(original_size)
            response.headers['X-Compressed-Size'] = str(compressed_size)
            response.headers['X-Compression-Ratio'] = f'{compression_ratio:.2f}'
            
            return response
        except Exception as e:
            return jsonify({'error': f'Error compressing image: {str(e)}'}), 500
    elif file_extension == 'pdf':
        temp_in_name = None
        temp_out_name = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_in:
                temp_in_name = temp_in.name
                file.save(temp_in.name)
                temp_in.flush()

            # Get original file size
            original_size = os.path.getsize(temp_in_name)

            reader = PdfReader(temp_in_name)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            
            # Compress content streams after pages are added to writer
            for page in writer.pages:
                page.compress_content_streams()

            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_out:
                temp_out_name = temp_out.name
                writer.write(temp_out)
                temp_out.flush()
            
            # Get compressed file size
            compressed_size = os.path.getsize(temp_out_name)
            
            # Calculate compression ratio
            compression_ratio = ((original_size - compressed_size) / original_size * 100) if original_size > 0 else 0
            
            # Read the compressed file into memory to send with custom headers
            with open(temp_out_name, 'rb') as f:
                pdf_data = io.BytesIO(f.read())
            
            response = send_file(
                pdf_data,
                mimetype='application/pdf',
                as_attachment=True,
                download_name='compressed.pdf'
            )
            
            # Add custom headers with file size information
            response.headers['X-Original-Size'] = str(original_size)
            response.headers['X-Compressed-Size'] = str(compressed_size)
            response.headers['X-Compression-Ratio'] = f'{compression_ratio:.2f}'
            
            return response
        except Exception as e:
            return jsonify({'error': f'Error compressing PDF: {str(e)}'}), 500
        finally:
            if temp_in_name and os.path.exists(temp_in_name):
                os.unlink(temp_in_name)
            if temp_out_name and os.path.exists(temp_out_name):
                os.unlink(temp_out_name)
    else:
        return jsonify({'error': 'Unsupported file type for compression'}), 400

@app.route('/')
def home():
    return 'PDF Unlocker Backend is running!'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

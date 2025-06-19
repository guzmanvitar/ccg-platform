from django import forms


class UploadFileForm(forms.Form):
    file = forms.FileField(label="Upload your genetic data (.vcf, .fasta .fastq)")

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        valid_extensions = [".vcf", ".fasta", "fastq"]
        if not any(uploaded_file.name.endswith(ext) for ext in valid_extensions):
            raise forms.ValidationError(
                "Invalid file type. Only .vcf and .txt files are allowed."
            )
        return uploaded_file
